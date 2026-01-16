# Dolphin Expr - Experiment System for Dolphin

A structured experiment management system for running, benchmarking, and analyzing Dolphin Language programs with configuration comparison, variable tracking, and large-scale automation support.

> **Language Policy**: This README and usage documentation are in English. Design documents (`docs/design/`) are in Chinese for internal team discussion. See [Documentation](docs/README.md) for details.

## 🚀 Quick Start

### Prerequisites

- Dolphin Language SDK (local development version)
- Python 3.8+
- Required dependencies (see [Installation Guide](docs/usage/quick_start/installation.md))

### 5-Minute Setup

```bash
# 1. Set up Dolphin SDK path
export DOLPHIN_SRC=/path/to/dolphin/src
# Or: export DOLPHIN_REPO=/path/to/dolphin (will use /src automatically)

# 2. Configure environment
source ./setup_env.sh

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your first experiment
./bin/create --name my_first_experiment --dolphins path/to/dolphins_folder

# 5. Run the experiment
./bin/run --name my_first_experiment
```

For detailed setup instructions, see [Getting Started Guide](docs/usage/quick_start/getting_started.md).

## 📁 Project Structure

```
dolphin-expr/
├── bin/                    # Experiment management scripts
│   ├── create             # Create new experiments
│   ├── run                # Run/manage experiments
│   └── analyst            # Experiment analysis tools
├── design/                # Experiment design area
│   └── [experiment_name]/
│       ├── spec.txt       # Experiment specification
│       ├── config/        # Configuration files
│       └── dolphins/      # DPH script files
├── benchmark/             # Benchmark test data
│   └── [benchmark_name]/
│       ├── benchmark.json # Benchmark data
│       └── benchmark.yaml # Benchmark configuration
├── env/                   # Experiment runtime environments
│   └── [experiment_run_timestamp]/
│       └── run_XXX/       # Individual run directories
├── docs/                  # Documentation
│   ├── usage/            # Usage documentation (English)
│   └── design/           # Design documentation (Chinese)
└── analyst/              # Experiment analysis tools
```

## 🎯 Key Features

- **🔧 Configuration Comparison**: Compare different model parameters and configurations
- **📊 Benchmark Testing**: Evaluate system performance with standardized test sets
- **📈 Variable Tracking**: Record and analyze key variables during execution
- **🚀 Parallel Execution**: Multi-threaded concurrent execution for large-scale experiments
- **🤖 Intelligent Analysis**: LLM-powered semantic comparison and execution analysis
- **🎯 Skill Validation**: Enforce required skill execution for quality assurance
- **📝 Trajectory Recording**: Detailed execution trace for debugging and analysis
- **🔄 Cross-Run Analysis**: Identify systematic issues across multiple runs

## 📖 Documentation

### Quick Start
- [Getting Started](docs/usage/quick_start/getting_started.md) - 5-minute quick start guide
- [Installation](docs/usage/quick_start/installation.md) - Detailed installation and setup

### Guides
- [Complete Guide (中文)](docs/usage/guides/complete_guide_zh.md) - Comprehensive Chinese guide
- [Analyst Guide](docs/usage/guides/analyst_guide.md) - Experiment analysis tools
- [Troubleshooting](docs/usage/guides/troubleshooting.md) - Common issues and solutions

### Configuration
- [CLI Reference](docs/usage/configuration/cli_reference.md) - Command-line interface reference
- [Experiment Spec](docs/usage/configuration/experiment_spec.md) - spec.txt configuration reference

### Design Documents (Chinese)
- [Optimization Framework](docs/design/optimization.md)
- [Context Loader Optimization](docs/design/context_loader_optimization.md)
- [Bird Middleware Comparison](docs/design/bird_middleware_comparison.md)

## 🔨 Common Commands

```bash
# Create a new experiment
./bin/create --name my_experiment --dolphins path/to/dolphins

# Run an experiment
./bin/run --name my_experiment

# Check experiment status
./bin/run --name my_experiment --status

# List all experiment environments
./bin/run --name my_experiment --list-envs

# Resume from a specific sample
./bin/run --name my_experiment --resume-from 3

# Analyze experiment results
./bin/analyst my_experiment_20250901_120000

# Analyze specific case execution
./bin/analyst my_experiment_20250901_120000 --analysis --run run_001 --case 001

# Cross-run analysis for problematic cases
./bin/analyst my_experiment_20250901_120000 --cross-run-analysis --max-accuracy 30 --summary
```

## 🧪 Example: Running a Benchmark

```bash
# 1. Create experiment with benchmark
./bin/create --name sql_benchmark --dolphins path/to/sql_agents

# 2. Configure spec.txt
cat > design/sql_benchmark/spec.txt << EOF
entrypoints: ["sql_agent"]
configs:
  - default: ["qwen-plus", "v3"]
variables:
  tools: ["[executeSQL, _cog_gen_sql]"]
must_execute: ["executeSQL"]
benchmark: "bird_dev"
num_run_cases: 10
threads: 4
EOF

# 3. Run the benchmark
./bin/run --name sql_benchmark

# 4. Analyze results
./bin/analyst sql_benchmark_YYYYMMDD_HHMMSS
```

## 🛠️ Development

### Dolphin Dependency

This project uses a **local development version** of Dolphin Language SDK. The dependency is configured through:

1. **Environment Variables**:
   - `DOLPHIN_SRC`: Path to dolphin/src directory
   - `DOLPHIN_REPO`: Path to dolphin repository root (will use /src)

2. **Setup Script**: `./setup_env.sh` configures PYTHONPATH

3. **Python Module**: `project_env.py` provides `ensure_dolphin_importable()`

See [Installation Guide](docs/usage/quick_start/installation.md) for detailed setup.

### Code Standards

- All code comments and docstrings must be in **English**
- All log messages must be in **English**
- Follow the coding standards in [AGENTS.md](AGENTS.md)

## 📊 Use Cases

1. **Configuration Comparison**: Compare different model parameters and token limits
2. **Benchmark Evaluation**: Evaluate system performance with standardized test sets
3. **Variable Analysis**: Track key variables during program execution
4. **Large-Scale Experiments**: Automated execution of multiple configuration combinations
5. **Intelligent Answer Evaluation**: LLM-based semantic comparison for benchmarks
6. **SQL Database Testing**: Custom comparators for SQL query result validation
7. **Skill Compliance Checking**: Ensure critical skills are executed in tests
8. **High-Performance Concurrent Experiments**: Multi-threaded execution for efficiency

## 🐛 Troubleshooting

### Common Issues

**Dolphin import error**:
```bash
# Set the environment variable
export DOLPHIN_SRC=/path/to/dolphin/src
source ./setup_env.sh
```

**Experiment run fails**:
```bash
# Check the log files
cat env/[experiment_run]/run_001/experiment_run_1.log

# Check individual case logs
cat env/[experiment_run]/run_001/console/case_001.log
```

For more issues and solutions, see [Troubleshooting Guide](docs/usage/guides/troubleshooting.md).

See [Complete Guide](docs/usage/guides/complete_guide_zh.md) for full version history.

## 📄 License

[Add your license information here]

## 🤝 Contributing

Contributions are welcome! Please follow the coding standards in [AGENTS.md](AGENTS.md).

## 📧 Contact

[Add contact information here]

---

**Note**: This is an experiment system for Dolphin Language. For Dolphin Language SDK documentation, please refer to the main Dolphin repository.
