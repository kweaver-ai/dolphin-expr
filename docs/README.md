# Dolphin Expr Documentation

欢迎查看 Dolphin Expr 项目文档。为了方便查阅，我们将文档分为了**使用文档**和**设计文档**两大类。

## 📖 Language Policy (语言政策)

- **Usage 文档 (使用文档)**: 英文为主 - 面向国际化使用和开发
- **Design 文档 (设计文档)**: 中文为主 - 面向团队内部技术讨论

## 📚 Usage (使用文档)

面向用户、实验运行者和日常开发者。

### 🚀 Quick Start (快速开始)
- [5分钟快速上手](usage/quick_start/getting_started.md): 从零到第一次成功运行。
- [安装与环境配置](usage/quick_start/installation.md): 环境依赖、安装步骤。

### 💡 Concepts (核心概念)
- [Agent 开发规范](usage/concepts/agent_standards.md): 代码风格、日志规范、国际化要求等。

### 📖 Guides (操作指南)
- [Analyst 快速参考](usage/guides/analyst_quick_reference.md): Analyst 工具英文快速参考（简明版）。
- [Analyst 分析器使用指南](usage/guides/analyst_guide.md): 如何分析实验结果、使用语义裁判、注入优化等（详细中文版）。
- [故障排除指南](usage/guides/troubleshooting.md): 常见问题与解决方案。
- [Context Loader 调试](usage/guides/context_loader_debugging.md): Context Loader 环境变量问题专项调试。

### ⚙️ Configuration (配置与参考)
- [CLI 命令行参考](usage/configuration/cli_reference.md): `run`, `create`, `analyst` 等命令的详细参数说明。
- [实验配置参考 (spec.txt)](usage/configuration/experiment_spec.md): 变量空间、采样策略、Benchmark 配置说明。

---

## 📐 Design (设计文档)

面向架构师、核心贡献者，包含系统原理、优化细节和选型对比。

- [优化框架设计](design/optimization.md): 系统整体优化策略与框架。
- [Context Loader 优化](design/context_loader_optimization.md): 上下文加载机制的优化细节。
- [Bird 中间件方案对比](design/bird_middleware_comparison.md): 不同中间件方案的选型对比分析。

---

## 🗄️ Archive (归档)

项目根目录的 `baks/` 目录存放中间过程或即将淘汰的文档：
- `baks/optimization/IMPLEMENTATION_SUMMARY.md`
- `baks/optimization/OPTIMIZATION_METHODS.md`
- `baks/optimization/PHASE2_IMPLEMENTATION_SUMMARY.md`
