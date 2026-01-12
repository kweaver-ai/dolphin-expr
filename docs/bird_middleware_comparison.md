# Bird 实验：KN 中间件（Context Loader）vs 直连 SQL 对比方案（推荐版）

目标：在 **不改动本仓库 Python 代码**（`bin/*`、`analyst/*`、`optimization/*`）的前提下，为 Bird 实验新增一个走 **KN 中间件（Context Loader）** 的 agent，并与当前 **直连 SQL（executeSQL）** 的 agent 做可重复、可量化对比。

本方案默认：KN 背后数据同源于 SQL（只是多一层中间件）。

---

## 推荐总览

- **推荐接入方式：Dynamic Tools（首选）**
  - 原因：你们的 `.adp`/`get_action_info` 协议天然产出 `_dynamic_tools`，且你已在主 dolphin 修复 `_load_dynamic_tools` 的新路径导入（不再依赖废弃的 `DolphinLanguageSDK.skill.*`）。
- **备选接入方式：MCP 封装（第二选择）**
  - 原因：隔离清晰、通用性强，但需要额外实现/部署一个 MCP server 做 HTTP 转发，落地成本更高。

---

## 1) 对比实验要回答的问题（指标定义）

对比维度（推荐全部保留）：

- **Accuracy**：以 Bird benchmark comparator 的最终判定为准
- **Latency**：每 case 的耗时分布（P50/P99）
- **Tool Calls**：工具调用次数/结构（`executeSQL` vs KN tools）
- **Stability**：失败率、重试次数、超时比例（如有）
- **Failure Taxonomy**：典型失败类型（条件缺失/排序 limit 不一致/召回错 schema/返回超集等）

推荐的实验形态：
- 先用 `num_run_cases=3` 冒烟确保链路通，再扩到 30/100 做稳定性与分布统计。

---

## 2) 现有 Bird 实验契约（保证对比“可比”）

Bird benchmark 的判定依赖：
- gold SQL 执行得到真值（rows）
- agent 输出的 `final_result` 转换后与真值比对

因此无论走直连 SQL 还是 KN 中间件，**新 agent 必须输出可比对结构**（推荐统一为表结构）：

- `final_result = {"columns": [...], "data": [...]}`  

不要只输出自然语言答案，否则 comparator 基本无法对齐。

---

## 3) 直连 SQL 基线（baseline）

当前基线 agent：
- `design/bird_baseline/dolphins/baseline.dph`
- `design/bird_baseline/dolphins/explore_based.dph`

共同特点：
- 直接调用 `executeSQL(datasource=$db_id, sql=...)` 获取结果

用途：
- 作为基线链路，记录 accuracy/latency/tool_calls

---

## 4) KN 中间件链路（推荐：Dynamic Tools）

### 4.1 你们工具集的关键点（来自 `.adp`）

`.adp` 工具集中（context loader 工具集）关键工具：
- `get_action_info`：返回行动信息；其 schema 定义了 `ActionRecallResponse`，包含：
  - `_dynamic_tools`：动态工具列表（每个元素是 `DynamicTool`）
  - `headers`：可选 HTTP headers

`DynamicTool` 的字段集合与 dolphin 动态工具加载逻辑对齐（必须确保实际返回也包含这些字段）：
- `name`
- `description`
- `parameters`（OpenAI function-call schema）
- `api_url`
- `original_schema`
- `fixed_params`
- `api_call_strategy`（**必须实际返回该字段**，dolphin 用它判断分支）

### 4.2 dolphin 动态工具加载要求（你已修复后的版本）

运行时流程（推荐）：
1) agent 先调用 `get_action_info`（提供 `kn_id` + `at_id` + `unique_identity`）
2) dolphin 从响应中识别 `_dynamic_tools`
3) `basic_code_block._load_dynamic_tools` 将其转成 `DynamicAPISkillFunction` 并注入 skillset
4) agent 继续调用这些新注入的工具完成查询，最后输出 `final_result`

### 4.3 新增 KN agent 的职责边界（推荐写法）

新 agent（例如 `kn_based.dph`）只做两件事：
- **工具发现**：通过 `get_action_info` 加载动态工具
- **结果对齐**：用动态工具查询/计算，最后输出 `{columns,data}`（且严格对齐排序/limit/null 规则）

它不需要知道底层是 SQL 还是图数据库；对比实验只观察结果与过程。

### 4.4 防作弊：必须加 `must_execute`

为了确保中间件链路真实参与对比，推荐在 spec 里加：
- `must_execute: ["get_action_info", "...至少一个动态工具名..."]`

这样可以避免 agent 走捷径回退到 `executeSQL`（即便你未来把 `executeSQL` 也启用在同一环境里）。

---

## 5) 备选：MCP 封装（推荐仅在 Dynamic Tools 不可用时使用）

做法：
- 写一个 MCP server（可以是独立 repo/服务），把 6 个 HTTP API 包装成 MCP tools
- 在 `global.yaml` 里启用 `mcp` 并配置该 server
- KN agent 直接调用 MCP tools 完成查询

优点：
- 标准化、隔离强、对 Dolphin 版本依赖更少

缺点：
- 需要额外开发/部署一个 MCP server（实验周期更长）

---

## 6) 实验落地步骤（推荐路径）

### 6.1 需要依次调整哪些内容（按顺序）

下面列表只包含“实验素材/配置”的变更，不涉及修改本仓库 Python 代码。

1) **准备环境变量与中间件地址（运行前）**
   - 确保运行时能访问 Context Loader 服务（例如把 `.adp` 里的 `server_url` 切到你可达的地址）。
   - 准备需要的鉴权 header/账号信息（建议走环境变量，不进仓库）。

2) **新增一个 KN agent（新增 `.dph` 文件）**
   - 位置：`design/bird_baseline/dolphins/kn_based.dph`（名称可自定）
   - 逻辑：
     - 先调用 `get_action_info`（传入 `kn_id/at_id/unique_identity`）拿到 `_dynamic_tools`
     - 再调用动态注入的工具完成查询/计算
     - 最后输出 `final_result={columns,data}`（严格对齐排序/limit/null）

3) **为对比实验更新 spec（只改实验参数，不动代码）**
   - 文件：`design/bird_baseline/spec.txt`
   - 建议改动：
     - `entrypoints`：同时包含基线与中间件 agent，例如 `["baseline", "kn_based"]`（或 `explore_based` vs `kn_based`）
     - `num_run_cases`：先设 3（冒烟），通过后再改到 30/100
     - `threads/num_samples`：先设小，确保可复现
     - `variables.tools`：按 entrypoint 需要配置（如果你的 DPH 用到了 `$tools`）

4) **开启 `must_execute` 防作弊（强烈推荐）**
   - 文件：`design/bird_baseline/spec.txt`
   - 新增/设置：`must_execute: ["get_action_info"]`（以及你期望必然发生的动态工具名）
   - 目的：确保 KN 路线一定经过中间件，而不是回退到 `executeSQL`。

5) **确保 Dolphin 运行时开启必要 skill（配置层）**
   - 文件：`design/bird_baseline/config/global.yaml`
   - 你至少需要：
     - `sql_skillkit`（用于 baseline）
     - 以及能执行 `get_action_info` 的工具所在机制（取决于你如何把 context loader 工具暴露给 dolphin：静态 tool、mcp、或其它）

6) **跑冒烟并产出对比报告**
   - 运行：`./bin/run --name bird_baseline`
   - 分析：`./bin/analyst <env_id> --general`

### 6.2 推荐的最小验证顺序（最省时间）

1) 先只跑 baseline（确认数据库/benchmark/comparator 正常）
2) 再只跑 `kn_based`（确认动态工具注入与返回结构 `columns/data` 正常）
3) 最后同一套 case 下同时跑两者，做 accuracy/latency/tool_calls 对比

---

## 7) 风险与缓解（推荐提前写进实验记录）

- **结果对齐风险**：中间件可能返回超集/乱序/空值处理不同 → 通过 agent 强约束排序、limit、去重、NULL 规则缓解
- **工具发现不稳定**：`get_action_info` 依赖 `at_id/unique_identity` 正确性 → 先用固定测试对象做冒烟
- **schema 漂移**：KN schema 与 bird 表结构不一致 → 用 `kn_schema_search/kn_search` 做显式校验并记录
