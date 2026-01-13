# Experiment Configuration Reference (spec.txt)

`spec.txt` is the core configuration file for experiment design, using YAML format. It defines the experiment's variable space, sampling strategy, benchmark settings, and runtime parameters.

The `bin/run` command reads this file and generates specific experiment runs based on variable combinations.

## Basic Structure Example

```yaml
# 1. Entrypoint Definition
entrypoints: ["kn_middleware", "another_agent"]

# 2. Global Configuration Overrides
configs:
  - default: ["k2"]  # Override default LLM in default.yaml
  - context_engineer.default_strategy: ["level"]

# 3. Variable Space
# Each key here becomes a variable (var) in dolphin runtime
# Values must be lists, system will sample combinations from these lists
variables:
  tools: ["[executeSQL]", "[executeSQL, _cog_gen_sql]"]
  explore_block_v2 : [true, false]
  
  # Environment variables passed to Runtime/Context Loader
  kn_id: ["bird_formula_1"]
  context_loader_base_url: ["http://localhost:8000"]

# 4. Sampling and Execution Control
num_samples: 5           # Total number of runs generated (experiment groups)
sample_method: RANDOM    # Sampling method: SEQ (sequential) / RANDOM (random)
threads: 1               # Concurrent execution threads (usually set to 1, concurrency controlled by underlying layer)

# 5. Benchmark Settings
benchmark: bird_dev      # Test set name (corresponds to data in benchmark/ directory)
num_run_cases: 10        # Number of cases per run (-1 means all)

# 6. Special Controls (optional)
output_variables: []     # Specify variable names to highlight in reports
case_filter:             # Case filter conditions (optional)
  db_id: ["financial", "retail"]

must_execute_by_entrypoint: # Mandatory execution checks for different entrypoints (for verification)
  kn_middleware: ["get_action_info"] 
```

## Field Details

### Core Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `entrypoints` | List[str] | Specify dolphin entry file names for experiment execution (without .dph). | `["main_agent"]` |
| `variables` | Map[str, List] | Define experiment variables. Each key is a variable name, value is a list of options. Each run selects one value. | See example above |
| `configs` | List[Map] | Override configuration items in `design/*/config/`. Values must be lists. | `- default: ["gpt-4"]` |
| `benchmark` | str | Specify test set name. System loads `benchmark/{name}.json` or corresponding directory. | `bird_dev` |

### Sampling and Execution

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `num_samples` | int | Number of experiment groups (runs) to generate. Number of configuration sets sampled from variable space. | 1 |
| `sample_method` | str | `SEQ`: Sequential variable combinations (grid search mode)<br>`RANDOM`: Random sampling of variable combinations | `SEQ` |
| `num_run_cases` | int | Number of test cases per run. Set to -1 to run all. | -1 |
| `threads` | int | Concurrency during experiment execution (usually run-level concurrency, or case-level thread pool size, depends on runner implementation). | 1 |

### Advanced Configuration

| Field | Type | Description |
|-------|------|-------------|
| `case_filter` | Map | Only benchmark cases meeting filter conditions will be executed. Supports filtering by field. |
| `must_execute_by_entrypoint` | Map | Verification configuration. Specifies that when a certain entrypoint runs, logs must contain certain strings, otherwise considered failed. |
| `output_variables` | List[str] | In `bin/analyst` reports, force these variables to be displayed as key columns. |

### Environment Variable Passing

Variables defined in the `variables` section starting with `context_loader_` or specific `kn_` variables are usually directly injected into Dolphin's runtime environment variables for use by underlying Context Loader or middleware.

Common environment variables:
- `kn_id`: Knowledge base ID
- `kn_at_id`: Knowledge base Access Token ID
- `context_loader_base_url`: Context Loader service address
- `context_loader_timeout_seconds`: Timeout setting

## Best Practices

1. **Small-scale verification**: First set `num_run_cases: 2` and `num_samples: 1` to ensure configuration is correct and process runs through.
2. **Variable control**: Try to vary only 1-2 core variables at a time, use `SEQ` sampling for controlled variable analysis.
3. **Comments**: `spec.txt` supports `#` comments, recommend annotating complex variable meanings.
