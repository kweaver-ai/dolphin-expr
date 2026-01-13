# Analyst Quick Reference

> **Note**: For comprehensive documentation in Chinese with all advanced features, see [analyst_guide.md](analyst_guide.md) (621 lines, includes semantic-driven optimization, detailed troubleshooting, etc.)

This tool automatically analyzes experiment results under `env/`, generating structured text reports and detailed CSV data.

## Quick Start

```bash
# General analysis (default mode)
./bin/analyst my_experiment_20250901_120000

# Execution analysis for specific case
./bin/analyst my_experiment_20250901_120000 --analysis --run run_001 --case 001

# Cross-run analysis
./bin/analyst my_experiment_20250901_120000 --cross-run-analysis --max-accuracy 30

# Simulation injection optimization
./bin/analyst my_experiment_20250901_120000 --sim-inject --case_id 001
```

## Core Features

### Analysis Capabilities
- 🔍 **Configuration Comparison**: Summarize key configs for each run
- 📊 **Accuracy Statistics**: Total cases, correct/incorrect counts, accuracy rates
- 🎯 **Model Grouping**: Compare multiple runs of same model
- 🔄 **Consistency Analysis**: Cross-run consistency and differences
- ⏱️ **Latency Analysis**: Real execution time based on log timestamps
- 🕸️ **Call Chain Analysis**: Tool usage, LLM calls, interaction rounds
- 🚨 **Error Analysis**: Common errors, warnings, health assessment

### Advanced Features
- 🧠 **AI Deep Analysis**: LLM-powered insights and recommendations
- 🎯 **Execution Analysis**: Deep dive into agent execution process
- 📚 **Knowledge Integration**: Load external knowledge files for enhanced analysis
- 🔄 **Cross-Run Analysis**: Systematic analysis across multiple runs
- 🧬 **Semantic Judge System**: Pure semantic evaluation (new)
- 🎛️ **Gradient Optimization**: Smart inject content optimizer (new)

## Common Usage Patterns

### 1. General Analysis

Generate comprehensive report and CSV:

```bash
./bin/analyst experiment_20250901_120000 --general
```

**Output**:
- `env/{experiment}/reports/{experiment}_general_report_{timestamp}.txt`
- `env/{experiment}/reports/{experiment}_general_report_{timestamp}.csv`

### 2. Execution Analysis

Analyze agent execution for specific or all failed cases:

```bash
# Single case
./bin/analyst experiment_id --analysis --run run_001 --case 001

# All failed cases in run
./bin/analyst experiment_id --analysis --run run_001

# With business knowledge
./bin/analyst experiment_id --analysis --run run_001 --knows knowledge.txt
```

**Output**: `env/{experiment}/{run}/analysis/case_XXX.txt`

### 3. Summary Analysis

Aggregate analysis results for a run:

```bash
./bin/analyst experiment_id --analysis --run run_001 --summary
```

**Output**: `env/{experiment}/{run}/summary_result.txt`

### 4. Cross-Run Analysis

Filter and analyze problematic cases across runs:

```bash
# Analyze cases with accuracy < 30%
./bin/analyst experiment_id --cross-run-analysis --max-accuracy 30 --summary
```

**Output**: `env/{experiment}/analysis/cross_run_summary_{timestamp}.txt`

### 5. Simulation Injection (Advanced)

Optimize difficult cases through semantic-driven iteration:

```bash
# Single case
./bin/analyst experiment_id --sim-inject --case_id 001

# Batch mode (all cases with accuracy < 10%)
./bin/analyst experiment_id --sim-inject --accuracy-threshold 10
```

## Parameters Reference

### General Parameters
- `--knows`: Business knowledge file or folder path
- `--general`: Generate general analysis report (default)

### Execution Analysis
- `--analysis`: Enable execution analysis mode
- `--run`: Specify run name (required)
- `--case`: Specify case number (optional)
- `--summary`: Generate summary report

### Cross-Run Analysis
- `--cross-run-analysis`: Enable cross-run analysis
- `--max-accuracy`: Maximum accuracy threshold (%)
- `--report-csv`: Specify CSV file path
- `--case`: Analyze specific case only

### Simulation Injection
- `--sim-inject`: Enable simulation injection
- `--case_id`: Specific case ID
- `--accuracy-threshold`: Batch mode threshold (default: 10)
- `--max-iterations`: Maximum iterations (default: 5)
- `--sim-timeout`: Timeout per execution (default: 500s)
- `--entrypoint`: Custom execution entrypoint
- `--inject-var`: Injection variable name (default: injects)

## Report Contents

### General Report Sections
1. **Experiment Configuration Comparison** - Key configs per run
2. **Configuration Factor Impact** - Factor influence on accuracy
3. **Accuracy Comparison** - Success/failure statistics
4. **Model Grouping** - Same-model run comparisons
5. **Consistency Analysis** - Cross-run consistency metrics
6. **Continuous Error Detection** - Systematic failure patterns
7. **Latency Analysis** - Execution time statistics
8. **Call Chain Analysis** - Tool usage and interaction patterns
9. **Log Error Analysis** - Common errors and warnings
10. **Health Assessment** - Overall run health evaluation
11. **AI Deep Analysis** - LLM-generated insights (optional)

## Output Files

### Analysis Reports
```
env/{experiment}/
├── reports/
│   ├── {experiment}_general_report_{timestamp}.txt
│   └── {experiment}_general_report_{timestamp}.csv
├── {run}/
│   ├── analysis/
│   │   └── case_XXX.txt
│   └── summary_result.txt
└── analysis/
    └── cross_run_summary_{timestamp}.txt
```

### Simulation Logs
```
simulation_logs/
├── case_{case_id}_iter_{N}.log
├── semantic_judge_{timestamp}.log
└── case_{case_id}_baseline.log
```

## Knowledge Path Resolution

When using `--knows` with relative paths:

1. Single run analysis: `{env}/{run}/<knows>`
2. Design directory: `design/{design_name}/<knows>`
3. Experiment root: `{env}/<knows>`
4. Project root / current directory

Absolute paths are used directly.

## Dependencies

- Python 3.10+
- pandas
- PyYAML

```bash
pip install -r requirements.txt
```

## Troubleshooting

### No Analysis Results
- Ensure experiment has completed at least one run
- Check `run_summary.yaml` files exist
- Verify benchmark comparator is configured

### Cross-Run Analysis Finds Nothing
- Run general analysis first to generate CSV
- Check accuracy threshold is reasonable
- Verify CSV file path

### Simulation Injection Fails
- Check `injects_deduce.dph` exists
- Verify dolphin environment configuration
- Increase `--sim-timeout` if needed

## Advanced Topics

For detailed information on:
- **Semantic-Driven Optimization**: See [analyst_guide.md](analyst_guide.md) §语义驱动系统详解
- **Gradient Optimization**: See [analyst_guide.md](analyst_guide.md) §注入优化器
- **Safety Constraints**: See [analyst_guide.md](analyst_guide.md) §安全约束保障
- **Technical Architecture**: See [analyst_guide.md](analyst_guide.md) §技术架构

## Related Documentation

- [CLI Reference](../configuration/cli_reference.md) - All command options
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
- [Experiment Configuration](../configuration/experiment_spec.md) - spec.txt format
