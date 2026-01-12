# 环境与依赖（Dolphin-Expr）

## 项目结构

```
dolphin-expr/
├── bin/                    # 实验管理脚本
│   ├── run                 # 运行实验
│   ├── create              # 创建实验
│   └── analyst             # 分析实验
├── benchmark/              # 基准测试数据
│   └── bird_dev/          # BIRD SQL 基准测试
├── design/                 # 实验设计
│   ├── bird_baseline/     # BIRD 基线实验
│   │   ├── config/global.yaml
│   │   ├── dolphins/*.dph
│   │   └── spec.txt
│   ├── search_or_query/
│   └── watsons_baseline/
├── env/                    # 实验运行环境（自动生成）
├── reports/                # （可选）分析报告输出目录
├── requirements.txt        # Python 依赖
├── setup_env.sh           # 环境设置脚本
└── README.md              # 项目文档
```

## 已完成的设置

✅ **依赖配置**
- 创建了 requirements.txt（实验系统自身依赖）
- 通过 `DOLPHIN_SRC`/`DOLPHIN_REPO` 连接主 dolphin 仓库（见下文）

✅ **实验数据**
- 复制了 bird_dev benchmark 数据
- 包含 benchmark.json, benchmark.yaml, init.py

✅ **配置文件**
- 创建了 bird_baseline/config/global.yaml
- 配置了 LLM、数据源等

✅ **脚本调整**
- 运行脚本使用 `python3`（要求 Python 3.10+）
- 去除硬编码本机路径，改用 `DOLPHIN_SRC`/`DOLPHIN_REPO` 与 `DOLPHIN_BIN`

✅ **版本控制**
- 初始化了 Git 仓库
- 添加了 .gitignore
- 创建了 2 个提交

## 依赖关系

本项目依赖主 dolphin 项目：
- **Dolphin 源码路径**: 通过 `DOLPHIN_SRC=/path/to/dolphin/src` 或 `DOLPHIN_REPO=/path/to/dolphin`
- **Dolphin 二进制**: 通过 PATH 中的 `dolphin`，或 `DOLPHIN_BIN=/path/to/dolphin`

所有 `bin/*` 脚本会自动尝试把 dolphin/src 加入 `PYTHONPATH`（见 `project_env.py`）。

## 使用方法

### 1. 查看实验环境
```bash
cd ~/lab/dolphin-expr
./bin/run --name bird_baseline --list-envs
```

### 2. 运行 BIRD 实验
```bash
# 当前 spec.txt 配置会运行 150 个测试用例，2个线程
./bin/run --name bird_baseline
```

### 3. 查看实验状态
```bash
./bin/run --name bird_baseline --status
```

### 4. 分析实验结果
```bash
./bin/analyst <experiment_env_id> --general
```

## 注意事项

1. **Python 版本**: 必须使用 Python 3.10+

2. **依赖更新**: 主 dolphin 项目的依赖请在其仓库内更新/安装（本仓库只维护实验系统自身依赖）。

3. **路径问题**:
   - 如果遇到路径问题，检查 bin/run 中的路径是否正确
   - 设计目录为 `design/`，运行输出为 `env/`

4. **配置文件**:
   - `design/*/config/global.yaml` 中的数据库路径需要存在（示例配置里可能是本机绝对路径）
   - 如果路径不存在，需要调整配置或准备数据

## 下一步

- 验证数据库文件路径是否存在
- 尝试运行一个小规模测试（修改 spec.txt 中的 num_run_cases）
- 根据需要调整 spec.txt 中的配置参数

## 项目定位

这个独立项目专注于实验性功能，保持对主 dolphin 项目的依赖关系：
- 实验系统代码独立维护
- 共享 dolphin 核心功能（通过 PYTHONPATH）
- 可以快速迭代实验设计而不影响主项目
