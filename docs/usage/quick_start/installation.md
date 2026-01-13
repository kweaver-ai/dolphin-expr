# Installation and Environment Setup

## Project Structure

```
dolphin-expr/
├── bin/                    # Experiment management scripts
│   ├── run                 # Run experiments
│   ├── create              # Create experiments
│   └── analyst             # Analyze experiments
├── benchmark/              # Benchmark test data
│   └── bird_dev/          # BIRD SQL benchmark
├── design/                 # Experiment designs
│   ├── bird_baseline/     # BIRD baseline experiment
│   │   ├── config/global.yaml
│   │   ├── dolphins/*.dph
│   │   └── spec.txt
│   ├── search_or_query/
│   └── watsons_baseline/
├── env/                    # Experiment runtime environments (auto-generated)
├── reports/                # (Optional) Analysis report output directory
├── requirements.txt        # Python dependencies
├── setup_env.sh           # Environment setup script
└── README.md              # Project documentation
```

## Prerequisites

✅ **Dependency Configuration**
- Created requirements.txt (experiment system dependencies)
- Connected to main dolphin repository via `DOLPHIN_SRC`/`DOLPHIN_REPO` (see below)

✅ **Experiment Data**
- Copied bird_dev benchmark data
- Includes benchmark.json, benchmark.yaml, init.py

✅ **Configuration Files**
- Created bird_baseline/config/global.yaml
- Configured LLM, data sources, etc.

✅ **Script Adjustments**
- Run scripts use `python3` (requires Python 3.10+)
- Removed hardcoded local paths, now using `DOLPHIN_SRC`/`DOLPHIN_REPO` and `DOLPHIN_BIN`

✅ **Version Control**
- Initialized Git repository
- Added .gitignore
- Created 2 commits

## Dependencies

This project depends on the main dolphin project:
- **Dolphin source path**: Via `DOLPHIN_SRC=/path/to/dolphin/src` or `DOLPHIN_REPO=/path/to/dolphin`
- **Dolphin binary**: Via `dolphin` in PATH, or `DOLPHIN_BIN=/path/to/dolphin`

All `bin/*` scripts will automatically add dolphin/src to `PYTHONPATH` (see `project_env.py`).

## Usage

### 1. View Experiment Environments
```bash
cd $PROJECT_ROOT
./bin/run --name bird_baseline --list-envs
```

### 2. Run BIRD Experiment
```bash
# Current spec.txt configuration runs 150 test cases with 2 threads
./bin/run --name bird_baseline
```

### 3. Check Experiment Status
```bash
./bin/run --name bird_baseline --status
```

### 4. Analyze Experiment Results
```bash
./bin/analyst <experiment_env_id> --general
```

## Important Notes

1. **Python Version**: Must use Python 3.10+

2. **Dependency Updates**: Dependencies for the main dolphin project should be updated/installed in its repository (this repository only maintains experiment system dependencies).

3. **Path Issues**:
   - If you encounter path issues, check if paths in bin/run are correct
   - Design directory is `design/`, runtime output is `env/`

4. **Configuration Files**:
   - Database paths in `design/*/config/global.yaml` must exist (example configs may contain local absolute paths)
   - If paths don't exist, adjust configuration or prepare data

## Next Steps

- Verify database file paths exist
- Try running a small-scale test (modify num_run_cases in spec.txt)
- Adjust configuration parameters in spec.txt as needed

## Project Positioning

This standalone project focuses on experimental features while maintaining dependencies on the main dolphin project:
- Experiment system code is independently maintained
- Shares dolphin core functionality (via PYTHONPATH)
- Can rapidly iterate on experiment designs without affecting the main project
