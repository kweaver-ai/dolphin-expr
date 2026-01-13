# Command Line Interface Reference

Unified experiment command entry point, covering "run/manage/analyze/create".

## Command Overview

- `bin/run`: Run/manage experiments (supports resume, status, environment enumeration, verbose)
- `bin/analyst`: Analyze experiments (general analysis, execution analysis, summary analysis)
- `bin/create`: Create new experiment design from existing `.dph` folder

## Run and Management (run)

### Features

- Complete experiment execution: Sample and execute according to `spec.txt`
- Experiment resume: Continue from specified sample number
- Status check: View running status of an execution environment
- Environment list: Enumerate all execution environments under `env`
- Detailed logging: Per-case `console/` logs, collect `profile/` in verbose mode

### Basic Usage

```bash
# Run experiment
./bin/run --name my_experiment

# Check latest execution status
./bin/run --name my_experiment --status

# List all execution environments for this experiment
./bin/run --name my_experiment --list-envs

# Specify execution environment to view status
./bin/run --name my_experiment --env-id my_experiment_20250828_052443 --status

# Resume from specified sample number
./bin/run --name my_experiment --resume-from 5

# Resume to sample 3 in specified execution environment
./bin/run --name my_experiment --env-id my_experiment_20250828_052443 --resume-from 3
```

### Parameters

- `--name`: Experiment name (required)
- `--verbose`: Enable detailed output and per-case `profile/` collection
- `--resume-from N`: Resume execution from Nth sample (run_NNN)
- `--env-id ID`: Specify execution environment (e.g., `my_experiment_20250828_052443`)
- `--status`: Display status of runs within execution environment
- `--list-envs`: List all execution environments for this experiment

### Experiment Environment and Output

Each execution environment is located at `env/{name}_{timestamp}/`, each sample generates a `run_XXX/` directory containing:

- `run_summary.yaml`: Summary of this run
- `console/`: Per-case logs (`case_XXX.log`)
- `profile/`: Performance profiling in verbose mode (archived by case)
- `history/`: Case process (includes `_all_stages`)
- `trajectory/`: Trajectory files (if enabled)
- `cmds/`: Command scripts to replay current run

Status indicators: ✅ COMPLETED / ❌ FAILED / ⏳ PARTIAL / 📁 CREATED

## Experiment Analysis (analyst)

Wrapper for `analyst` analyzer, providing four analysis modes:

- **General analysis** (default/`--general`): Generate comprehensive report and CSV
- **Execution analysis** (`--analysis --run`): Agent execution process analysis, supports single case and batch analysis
- **Summary analysis** (`--analysis --run --summary`): Summarize analysis artifacts under run
- **Cross-run analysis** (`--cross-run-analysis`): Filter problem cases based on accuracy threshold, supports cross-run summary analysis

### Core Features

- **Batch analysis**: Automatically identify failed cases and perform batch analysis
- **Business knowledge integration**: Support loading external knowledge files in execution and summary analysis
- **Result persistence**: Analysis results automatically saved, supports caching and reuse
- **Cache priority**: If analysis report exists for corresponding case, it will be skipped; to re-analyze, delete the report file and run again
- **Cross-run summary**: Filter low-accuracy cases, perform systematic cross-run analysis
- **Report localization**: All report files saved in experiment directory for easy management

### Usage

```bash
# 1) General analysis (default/explicit) - Generate comprehensive report and CSV
./bin/analyst my_experiment_20250901_120000
./bin/analyst my_experiment_20250901_120000 --general

# 2) Execution process analysis (single case or batch)
# Analyze single case
./bin/analyst my_experiment_20250901_120000 --analysis --run run_001 --case 001

# Batch analyze failed cases
./bin/analyst my_experiment_20250901_120000 --analysis --run run_001

# Analyze with business knowledge
./bin/analyst my_experiment_20250901_120000 --analysis --run run_001 --knows knowledge.txt
./bin/analyst my_experiment_20250901_120000 --analysis --run run_001 --knows ./knowledge_folder/

# 3) Summary analysis (requires run)
./bin/analyst my_experiment_20250901_120000 --analysis --run run_001 --summary

# Summary analysis with business knowledge
./bin/analyst my_experiment_20250901_120000 --analysis --run run_001 --summary --knows knowledge.txt
./bin/analyst my_experiment_20250901_120000 --analysis --run run_001 --summary --knows ./knowledge/

# 4) Cross-run analysis (new feature)
# Analyze cases with accuracy below 30%
./bin/analyst my_experiment_20250901_120000 --cross-run-analysis --max-accuracy 30

# Cross-run analysis and generate summary report
./bin/analyst my_experiment_20250901_120000 --cross-run-analysis --max-accuracy 30 --summary

# Use specific CSV file and business knowledge
./bin/analyst my_experiment_20250901_120000 --cross-run-analysis --max-accuracy 30 --summary --report-csv ./custom.csv --knows ./knowledge/

# Cross-run analysis and summary for single case only (supports case_001 / 001 / 1)
./bin/analyst my_experiment_20250901_120000 --cross-run-analysis --max-accuracy 100 --summary --case 001
./bin/analyst my_experiment_20250901_120000 --cross-run-analysis --max-accuracy 100 --summary --report-csv ./custom.csv --case case_001

# Support absolute paths
./bin/analyst /full/path/to/env/my_experiment_20250901_120000 --general
```

### Parameters

**General parameters**:
- `--knows`: Business knowledge file or folder path, applicable to execution analysis, summary analysis, and cross-run analysis

**Execution analysis parameters**:
- `--run`: Specify run name (required)
- `--case`: Specify case number (optional, batch analysis if not specified)
- `--failed-only`: Explicitly specify to analyze only failed cases (default behavior)

**Cross-run analysis parameters**:
- `--max-accuracy`: Maximum accuracy threshold (percentage, required)
- `--report-csv`: Specify general report CSV file path (optional, automatically finds latest by default)
- `--summary`: Generate cross-run summary analysis report (optional)
- `--case`: Specify to analyze only one case, and summarize only that case when `--summary` is enabled (supports `case_001`, `001`, or `1`)

### Analysis Output

- **General analysis**:
  - `env/{experiment}/reports/{experiment}_general_report_{timestamp}.txt`
  - `env/{experiment}/reports/{experiment}_general_report_{timestamp}.csv` (includes overall accuracy column)

- **Execution analysis**:
  - Output to console (marked with `===ANALYSIS_START=== ... ===ANALYSIS_END===`)
  - Automatically saved to: `env/{experiment}/{run}/analysis/case_XXX.txt`
  - Supports caching, re-analyzing same case will use cached results

- **Summary analysis**:
  - Written to corresponding run: `env/{experiment}/{run}/summary_result.txt`
  - Summarizes based on saved analysis results
  - Supports business knowledge enhancement, provides more precise improvement suggestions

- **Cross-run analysis**:
  - Analysis results saved to each run's analysis directory
  - Summary report: `env/{experiment}/analysis/cross_run_summary_{timestamp}.txt`
  - Includes cross-run high-frequency error analysis, missing business knowledge identification, and improvement suggestions

### Knowledge Path Resolution Rules (--knows)
- Search order for relative paths:
  1) Single run summary/execution analysis: Priority `{env}/{run}/<knows>`
  2) Design directory: `design/{design_name}/<knows>` (e.g., watsons_baseline_20250914_XXXX -> design name watsons_baseline)
  3) Experiment environment root: `{env}/<knows>`
  4) Project root, current working directory
- Absolute path: Use directly

For more analysis dimensions and capabilities, see `usage/guides/analyst_guide.md`.

## Create Experiment (create)

Create a new experiment design from existing `.dph` folder:

```bash
./bin/create --name my_experiment --dolphins path/to/dph_folder
```

Will generate:

- `design/my_experiment/spec.txt`
- `design/my_experiment/config/`
- `design/my_experiment/dolphins/` (copy source `.dph`)
- `design/my_experiment/runs/`

## Common Scenarios

- Create and run:
  - `./bin/create --name demo --dolphins ./examples/dolphins`
  - `./bin/run --name demo`
- Resume from checkpoint:
  - `./bin/run --name demo --status`
  - `./bin/run --name demo --resume-from 3`
- Historical environment review:
  - `./bin/run --name demo --list-envs`
  - `./bin/run --name demo --env-id demo_20250901_120000 --status`
- Result analysis:
  - `./bin/analyst demo_20250901_120000 --general`
  - `./bin/analyst demo_20250901_120000 --analysis --run run_001 --case 001`
  - `./bin/analyst demo_20250901_120000 --analysis --run run_001`  # Batch analysis
  - `./bin/analyst demo_20250901_120000 --analysis --run run_001 --knows ./docs/`  # With knowledge
  - `./bin/analyst demo_20250901_120000 --analysis --run run_001 --summary --knows ./docs/`  # Summary+knowledge
