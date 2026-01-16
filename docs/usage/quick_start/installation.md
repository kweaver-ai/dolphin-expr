# Installation Guide

This guide provides detailed instructions for installing and configuring the Dolphin Expr experiment system.

## Table of Contents

- [System Requirements](#system-requirements)
- [Dolphin SDK Setup](#dolphin-sdk-setup)
- [Python Environment](#python-environment)
- [Project Installation](#project-installation)
- [Configuration](#configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## System Requirements

### Operating System
- **Linux**: Ubuntu 18.04+, CentOS 7+, or similar
- **macOS**: 10.15 (Catalina) or later
- **Windows**: WSL2 (Windows Subsystem for Linux)

### Software Dependencies
- **Python**: 3.8 or higher (3.9+ recommended)
- **Git**: For version control and repository management
- **Shell**: bash or zsh

### Hardware Recommendations
- **CPU**: 2+ cores (4+ cores recommended for parallel execution)
- **RAM**: 4GB minimum (8GB+ recommended)
- **Disk Space**: 2GB for the system + space for experiment data

## Dolphin SDK Setup

The Dolphin Expr system requires a **local development version** of the Dolphin Language SDK. You cannot use a pip-installed version.

### Step 1: Obtain Dolphin SDK

```bash
# Clone the Dolphin Language repository (if you don't have it)
git clone https://github.com/your-org/dolphin-language.git
cd dolphin-language

# Or navigate to your existing Dolphin repository
cd /path/to/existing/dolphin-language
```

### Step 2: Configure Environment Variables

You have two options:

#### Option A: DOLPHIN_SRC (Recommended)

Points directly to the `src` directory:

```bash
export DOLPHIN_SRC=/path/to/dolphin-language/src
```

#### Option B: DOLPHIN_REPO

Points to the repository root (automatically uses `/src`):

```bash
export DOLPHIN_REPO=/path/to/dolphin-language
```

### Step 3: Make It Permanent

Add the export command to your shell configuration file:

**For bash** (`~/.bashrc`):
```bash
echo 'export DOLPHIN_SRC=/path/to/dolphin-language/src' >> ~/.bashrc
source ~/.bashrc
```

**For zsh** (`~/.zshrc`):
```bash
echo 'export DOLPHIN_SRC=/path/to/dolphin-language/src' >> ~/.zshrc
source ~/.zshrc
```

### Step 4: Verify Dolphin SDK

```bash
# Run the setup script
source ./setup_env.sh

# Expected output:
# ✓ PYTHONPATH configured for dolphin SDK
#   Dolphin source: /path/to/dolphin-language/src
```

If you see an error, check that:
1. The path exists: `ls $DOLPHIN_SRC`
2. It contains Python files: `ls $DOLPHIN_SRC/dolphin/`

## Python Environment

### Option 1: System Python (Simple)

```bash
# Check Python version
python3 --version  # Should be 3.8+

# Install dependencies
pip3 install -r requirements.txt
```

### Option 2: Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Linux/macOS
# Or: venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Option 3: Conda Environment

```bash
# Create conda environment
conda create -n dolphin-expr python=3.9

# Activate it
conda activate dolphin-expr

# Install dependencies
pip install -r requirements.txt
```

## Project Installation

### Step 1: Clone the Repository

```bash
# Clone the Dolphin Expr repository
git clone https://github.com/your-org/dolphin-expr.git
cd dolphin-expr
```

Or if you already have it:

```bash
cd /path/to/dolphin-expr
```

### Step 2: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
```

**Dependencies installed**:
- `pyyaml>=6.0` - YAML configuration parsing
- `pandas>=2.0` - Data analysis and CSV handling
- `numpy>=1.24` - Numerical operations
- `sqlalchemy>=2.0` - Database operations (for SQL benchmarks)
- `requests>=2.31` - HTTP requests (for API calls)

### Step 3: Make Scripts Executable

```bash
# Make all scripts in bin/ executable
chmod +x bin/*
```

### Step 4: Verify Installation

```bash
# Check that scripts are executable
./bin/run --help
./bin/create --help
./bin/analyst --help
```

## Configuration

### LLM Configuration

The system uses LLM models configured in `design/[experiment_name]/config/global.yaml`.

Example configuration:

```yaml
default: qwen-plus
clouds:
  default: aliyun
  aliyun:
    api: https://dashscope.aliyuncs.com/compatible-mode/v1
    api_key: "${ALIYUN_API_KEY}"
llms:
  qwen-plus:
    cloud: aliyun
    model_name: qwen-plus-latest
    type_api: openai
```

**Set up API keys**:

```bash
# Add to your shell configuration
export ALIYUN_API_KEY="your-api-key-here"
export DEEPSEEK_API_KEY="your-deepseek-key"
export ZHIPU_API_KEY="your-zhipu-key"
```

### Database Configuration (Optional)

For SQL benchmarks, configure data sources in `global.yaml`:

```yaml
ontology:
  dataSources:
    - name: my_database
      type: SQLITE
      database: /path/to/database.sqlite
```

**Important**: Use absolute paths or environment variables, not hardcoded user paths.

## Verification

### Test 1: Environment Check

```bash
# Run setup script
source ./setup_env.sh

# Should output:
# ✓ PYTHONPATH configured for dolphin SDK
#   Dolphin source: /path/to/dolphin/src
```

### Test 2: Python Import

```bash
# Test dolphin import
python3 -c "import dolphin; print('✓ Dolphin SDK imported successfully')"
```

### Test 3: Create Test Experiment

```bash
# Create a test experiment
./bin/create --name test_install --dolphins design/bird_baseline/dolphins

# Should create:
# design/test_install/
```

### Test 4: Check Status

```bash
# This should work even without running
./bin/run --name test_install --status

# Expected: "No environment found" (normal for new experiment)
```

## Troubleshooting

### Issue: "Cannot import dolphin"

**Symptoms**:
```
ImportError: No module named 'dolphin'
```

**Solutions**:

1. **Check environment variable**:
   ```bash
   echo $DOLPHIN_SRC
   # Should output: /path/to/dolphin/src
   ```

2. **Verify path exists**:
   ```bash
   ls $DOLPHIN_SRC/dolphin/
   # Should list Python files
   ```

3. **Re-run setup**:
   ```bash
   source ./setup_env.sh
   ```

4. **Check PYTHONPATH**:
   ```bash
   echo $PYTHONPATH
   # Should include your DOLPHIN_SRC
   ```

### Issue: "Permission denied" when running scripts

**Symptoms**:
```
bash: ./bin/run: Permission denied
```

**Solution**:
```bash
chmod +x bin/*
```

### Issue: "Module not found" for dependencies

**Symptoms**:
```
ModuleNotFoundError: No module named 'yaml'
```

**Solution**:
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or install specific package
pip install pyyaml
```

### Issue: API key not found

**Symptoms**:
```
Error: API key not configured
```

**Solution**:
```bash
# Set API key
export ALIYUN_API_KEY="your-key-here"

# Make it permanent
echo 'export ALIYUN_API_KEY="your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

### Issue: Database connection error

**Symptoms**:
```
Error: Could not connect to database
```

**Solution**:

1. **Check database path** in `global.yaml`:
   ```yaml
   database: /absolute/path/to/database.sqlite
   ```

2. **Verify file exists**:
   ```bash
   ls /path/to/database.sqlite
   ```

3. **Check permissions**:
   ```bash
   ls -l /path/to/database.sqlite
   # Should be readable
   ```

## Advanced Configuration

### Using Custom Python Interpreter

```bash
# Specify Python interpreter in shebang
# Edit bin/run, bin/create, etc. if needed
#!/usr/bin/env python3
```

### Using Different Dolphin Versions

```bash
# Switch between different Dolphin versions
export DOLPHIN_SRC=/path/to/dolphin-v1/src
source ./setup_env.sh

# Or
export DOLPHIN_SRC=/path/to/dolphin-v2/src
source ./setup_env.sh
```

### Setting Up Multiple Environments

```bash
# Create separate virtual environments
python3 -m venv venv-dev
python3 -m venv venv-prod

# Use different environments
source venv-dev/bin/activate   # For development
source venv-prod/bin/activate  # For production
```

## Next Steps

Now that you have Dolphin Expr installed:

1. **Quick Start**: Follow the [Getting Started Guide](getting_started.md) to run your first experiment
2. **Learn More**: Read the [Complete Guide](../guides/complete_guide_zh.md) for advanced features
3. **Configure**: Check [CLI Reference](../configuration/cli_reference.md) for all command options
4. **Troubleshoot**: See [Troubleshooting Guide](../guides/troubleshooting.md) for common issues

## Getting Help

If you encounter issues not covered here:

1. Check the [Troubleshooting Guide](../guides/troubleshooting.md)
2. Review the [Complete Guide](../guides/complete_guide_zh.md)
3. Check the project's issue tracker
4. Contact the development team

---

**Installation complete!** You're ready to start running experiments with Dolphin Expr.
