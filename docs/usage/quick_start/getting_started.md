# Getting Started (5-Minute Quickstart)

This guide will help you run your first experiment in 5 minutes.

## Prerequisites

- Python 3.10+
- Access to main dolphin repository
- Git

## Step 1: Clone and Setup (2 min)

```bash
# Clone the repository
git clone <repository-url> dolphin-expr
cd dolphin-expr

# Set up dolphin dependency
export DOLPHIN_REPO=/path/to/your/dolphin/repo
# OR
export DOLPHIN_SRC=/path/to/your/dolphin/src

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Verify Installation (1 min)

```bash
# List available experiments
ls design/

# Check if bird_baseline exists
./bin/run --name bird_baseline --list-envs
```

Expected output: Should show experiment structure or empty environment list (if never run before).

## Step 3: Run Your First Experiment (2 min)

```bash
# Run a small test with 3 cases
# First, edit spec.txt to reduce test size
cd design/bird_baseline
# Modify spec.txt: set num_run_cases: 3

# Run the experiment
cd ../..
./bin/run --name bird_baseline
```

You should see:
- Experiment environment created under `env/bird_baseline_<timestamp>/`
- Progress logs for each case
- Final summary in `run_summary.yaml`

## Step 4: Check Results (30 sec)

```bash
# Check experiment status
./bin/run --name bird_baseline --status

# View the latest environment
ls env/bird_baseline_*/
```

Expected structure:
```
env/bird_baseline_20250113_145500/
├── run_001/
│   ├── run_summary.yaml    # Results summary
│   ├── console/            # Per-case logs
│   └── history/            # Execution history
└── reports/                # Analysis reports (after running analyst)
```

## Next Steps

### Analyze Results
```bash
# Generate analysis report
./bin/analyst bird_baseline_<timestamp> --general
```

### Run More Cases
Edit `design/bird_baseline/spec.txt`:
```yaml
num_run_cases: 10  # or -1 for all cases
```

### Try Different Configurations
Modify variables in `spec.txt`:
```yaml
variables:
  tools: ["[executeSQL]"]
  explore_block_v2: [true]
```

### Learn More
- [Installation Guide](installation.md) - Detailed setup instructions
- [CLI Reference](../configuration/cli_reference.md) - All available commands
- [Experiment Configuration](../configuration/experiment_spec.md) - spec.txt format
- [Analyst Guide](../guides/analyst_guide.md) - Advanced analysis features

## Troubleshooting

### "Command not found: dolphin"
Set `DOLPHIN_BIN` environment variable:
```bash
export DOLPHIN_BIN=/path/to/dolphin/binary
```

### "Module not found" errors
Ensure dolphin source is in PYTHONPATH:
```bash
export PYTHONPATH=$DOLPHIN_SRC:$PYTHONPATH
```

### Database path errors
Check `design/bird_baseline/config/global.yaml` and update database paths to match your system.

## Quick Reference

| Task | Command |
|------|---------|
| Run experiment | `./bin/run --name <experiment>` |
| Check status | `./bin/run --name <experiment> --status` |
| List environments | `./bin/run --name <experiment> --list-envs` |
| Analyze results | `./bin/analyst <env_id> --general` |
| Create new experiment | `./bin/create --name <name> --dolphins <path>` |

---

**Congratulations!** 🎉 You've successfully run your first dolphin-expr experiment. Check out the guides for more advanced features.
