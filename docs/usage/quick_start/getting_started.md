# Getting Started with Dolphin Expr

This guide will help you set up and run your first experiment in **5 minutes**.

## Prerequisites

Before you begin, ensure you have:

- **Dolphin Language SDK** (local development version)
- **Python 3.8 or higher**
- **Git** (for cloning repositories)
- **Basic terminal/command-line knowledge**

## Step 1: Set Up Dolphin SDK (2 minutes)

The Dolphin Expr system requires a local development version of the Dolphin Language SDK.

### Option A: Using DOLPHIN_SRC

```bash
# Point to the dolphin/src directory
export DOLPHIN_SRC=/path/to/dolphin/src
```

### Option B: Using DOLPHIN_REPO

```bash
# Point to the dolphin repository root (will automatically use /src)
export DOLPHIN_REPO=/path/to/dolphin
```

### Verify Setup

```bash
# Run the setup script
source ./setup_env.sh

# You should see:
# ✓ PYTHONPATH configured for dolphin SDK
#   Dolphin source: /path/to/dolphin/src
```

**Tip**: Add the export command to your `~/.bashrc` or `~/.zshrc` to make it permanent.

## Step 2: Install Dependencies (1 minute)

```bash
# Install required Python packages
pip install -r requirements.txt
```

The system requires:
- `pyyaml>=6.0` - Configuration file parsing
- `pandas>=2.0` - Data analysis
- `numpy>=1.24` - Numerical operations
- `sqlalchemy>=2.0` - Database operations
- `requests>=2.31` - HTTP requests

## Step 3: Create Your First Experiment (1 minute)

```bash
# Create a new experiment
./bin/create --name my_first_experiment --dolphins path/to/your/dolphins_folder
```

This creates:
- `design/my_first_experiment/` - Experiment design directory
- `design/my_first_experiment/spec.txt` - Experiment specification
- `design/my_first_experiment/config/` - Configuration files
- `design/my_first_experiment/dolphins/` - DPH script files (copied from your folder)

## Step 4: Configure Your Experiment (30 seconds)

Edit `design/my_first_experiment/spec.txt`:

```yaml
# Basic configuration
entrypoints: ["main.dph"]  # or ["agent_name"] for agent mode
configs:
  - default: ["qwen-plus"]
variables:
  query: "What is the capital of France?"
num_samples: 1
sample_method: SEQ
```

**Quick explanation**:
- `entrypoints`: The DPH file or agent to run
- `configs`: LLM model configuration
- `variables`: Input variables for your program
- `num_samples`: Number of times to run

## Step 5: Run Your Experiment (30 seconds)

```bash
# Run the experiment
./bin/run --name my_first_experiment
```

You'll see output like:

```
Experiment: my_first_experiment
Run directory: env/my_first_experiment_20250116_140000/run_001
Running sample 1/1...
✓ Sample 1 completed
Experiment completed successfully!
```

## Step 6: Check Results (30 seconds)

```bash
# View experiment status
./bin/run --name my_first_experiment --status

# Check the results
cat env/my_first_experiment_*/run_001/run_summary.yaml
```

## 🎉 Success!

You've successfully:
- ✅ Set up the Dolphin Expr environment
- ✅ Created your first experiment
- ✅ Configured and ran it
- ✅ Viewed the results

## Next Steps

### Run a Benchmark Test

```bash
# Create a benchmark experiment
./bin/create --name benchmark_test --dolphins path/to/dolphins

# Configure with a benchmark
cat > design/benchmark_test/spec.txt << EOF
entrypoints: ["sql_agent"]
configs:
  - default: ["qwen-plus"]
benchmark: "bird_dev"
num_run_cases: 5
EOF

# Run it
./bin/run --name benchmark_test

# Analyze results
./bin/analyst benchmark_test_*
```

### Explore Advanced Features

- **Configuration Comparison**: Test multiple models simultaneously
- **Parallel Execution**: Speed up with multi-threading
- **Variable Tracking**: Monitor key variables during execution
- **Intelligent Analysis**: Use LLM-powered analysis tools

## Common First-Time Issues

### Issue: "Cannot import dolphin"

**Solution**:
```bash
# Make sure DOLPHIN_SRC or DOLPHIN_REPO is set
export DOLPHIN_SRC=/path/to/dolphin/src
source ./setup_env.sh

# Verify it's in your PYTHONPATH
echo $PYTHONPATH
```

### Issue: "Experiment creation failed"

**Solution**:
```bash
# Make sure your dolphins folder exists and contains .dph files
ls path/to/dolphins_folder/*.dph

# Use absolute path if relative path doesn't work
./bin/create --name my_experiment --dolphins $PWD/path/to/dolphins
```

### Issue: "Command not found: ./bin/run"

**Solution**:
```bash
# Make sure you're in the project root directory
cd /path/to/dolphin-expr

# Make scripts executable
chmod +x bin/*
```

## Learning Resources

- **[Installation Guide](installation.md)**: Detailed installation and configuration
- **[Complete Guide (中文)](../guides/complete_guide_zh.md)**: Comprehensive Chinese documentation
- **[CLI Reference](../configuration/cli_reference.md)**: All command-line options
- **[Experiment Spec Reference](../configuration/experiment_spec.md)**: spec.txt configuration details
- **[Troubleshooting Guide](../guides/troubleshooting.md)**: Common issues and solutions

## Quick Reference Card

```bash
# Environment Setup
export DOLPHIN_SRC=/path/to/dolphin/src
source ./setup_env.sh

# Experiment Management
./bin/create --name <name> --dolphins <path>
./bin/run --name <name>
./bin/run --name <name> --status
./bin/run --name <name> --list-envs
./bin/run --name <name> --resume-from <N>

# Analysis
./bin/analyst <experiment_env>
./bin/analyst <experiment_env> --analysis --run <run> --case <case>
./bin/analyst <experiment_env> --cross-run-analysis --max-accuracy 30
```

---

**Ready to dive deeper?** Check out the [Complete Guide](../guides/complete_guide_zh.md) for advanced features and best practices.
