# Dolphin Expr Documentation

欢迎查看 Dolphin Expr 项目文档。为了方便查阅，我们将文档分为了**使用文档**和**设计文档**两大类。

## 📖 Language Policy (语言政策)

- **Usage 文档 (使用文档)**: 英文为主 - 面向国际化使用和开发
- **Design 文档 (设计文档)**: 中文为主 - 面向团队内部技术讨论

## 📚 Usage (使用文档)

面向用户、实验运行者和日常开发者。

### 🚀 Quick Start (快速开始)
- [Getting Started](usage/quick_start/getting_started.md): 5-minute quick start guide - from zero to first successful run
- [Installation Guide](usage/quick_start/installation.md): Detailed installation, environment setup, and troubleshooting

### 💡 Concepts (核心概念)
- [Agent 开发规范](usage/concepts/agent_standards.md): 代码风格、日志规范、国际化要求等。

### 📖 Guides (操作指南)
- [Complete Guide (完整指南)](usage/guides/complete_guide_zh.md): Comprehensive Chinese guide with all features and examples
- [Analyst Quick Reference](usage/guides/analyst_quick_reference.md): Analyst tool quick reference (concise English version)
- [Analyst Guide (分析器使用指南)](usage/guides/analyst_guide.md): How to analyze experiment results, use semantic comparison, injection optimization, etc. (detailed Chinese version)
- [Troubleshooting Guide](usage/guides/troubleshooting.md): Common issues and solutions
- [Context Loader Debugging](usage/guides/context_loader_debugging.md): Context Loader environment variable troubleshooting

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
