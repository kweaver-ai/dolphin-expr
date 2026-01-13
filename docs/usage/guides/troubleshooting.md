# Troubleshooting Guide

Common issues and solutions when working with dolphin-expr.

## Environment and Setup Issues

### Issue: "Command not found: dolphin"

**Symptoms**: Running `./bin/run` fails with dolphin command not found.

**Solution**:
```bash
# Option 1: Set DOLPHIN_BIN
export DOLPHIN_BIN=/path/to/dolphin/binary

# Option 2: Add dolphin to PATH
export PATH=/path/to/dolphin/bin:$PATH

# Verify
which dolphin
```

### Issue: "Module not found" errors

**Symptoms**: Python import errors for dolphin modules.

**Solution**:
```bash
# Set DOLPHIN_SRC or DOLPHIN_REPO
export DOLPHIN_SRC=/path/to/dolphin/src
# OR
export DOLPHIN_REPO=/path/to/dolphin

# Verify
echo $DOLPHIN_SRC
python3 -c "import sys; print(sys.path)"
```

### Issue: Environment variables not passed to runtime

**Symptoms**: Agent uses default values instead of configured environment variables (e.g., `x-account-id: "test"`).

**Root Cause**: Non-interactive processes don't automatically load `~/.bashrc`.

**Solutions**:

1. **Set in startup script** (Recommended):
```python
# In bin/run
import os
env = os.environ.copy()
env['CONTEXT_LOADER_ACCOUNT_ID'] = 'your-account-id'
env['CONTEXT_LOADER_BASE_URL'] = 'http://your-server:port'
subprocess.run(cmd_parts, env=env)
```

2. **Use .env file**:
```bash
# Create .env in project root
CONTEXT_LOADER_ACCOUNT_ID=your-account-id
CONTEXT_LOADER_BASE_URL=http://your-server:port
```

3. **Export before running**:
```bash
export CONTEXT_LOADER_ACCOUNT_ID=your-account-id
./bin/run --name experiment
```

For detailed Context Loader debugging, see [Context Loader Debugging](context_loader_debugging.md).

## Experiment Execution Issues

### Issue: Database path errors

**Symptoms**: 
```
FileNotFoundError: Database not found at /path/to/database
```

**Solution**:
```bash
# Check config file
cat design/your_experiment/config/global.yaml

# Update database paths to match your system
# Edit the datasources section
```

### Issue: Experiment fails immediately

**Symptoms**: All cases fail with same error.

**Diagnosis**:
```bash
# Check experiment status
./bin/run --name experiment --status

# View first case log
cat env/experiment_*/run_001/console/case_001.log

# Check for configuration errors
cat env/experiment_*/run_001/run_summary.yaml
```

**Common causes**:
- Invalid entrypoint in spec.txt
- Missing required variables
- Incorrect benchmark path

### Issue: Partial completion (some cases succeed, some fail)

**Symptoms**: Status shows ⏳ PARTIAL.

**Solution**:
```bash
# Resume from last checkpoint
./bin/run --name experiment --resume-from N

# Where N is the last completed run number
```

## Analysis Issues

### Issue: Analyst fails to generate report

**Symptoms**: `./bin/analyst` command fails or produces empty report.

**Diagnosis**:
```bash
# Check if experiment completed
./bin/run --name experiment --status

# Verify experiment environment exists
ls env/experiment_*/

# Check for run_summary.yaml files
find env/experiment_* -name "run_summary.yaml"
```

**Solution**:
- Ensure experiment has completed at least one run
- Check that benchmark comparator is configured correctly
- Verify CSV output is generated

### Issue: Cross-run analysis finds no cases

**Symptoms**: `--cross-run-analysis` reports no cases found.

**Solution**:
```bash
# First run general analysis to generate CSV
./bin/analyst experiment_id --general

# Then run cross-run analysis
./bin/analyst experiment_id --cross-run-analysis --max-accuracy 30
```

## Performance Issues

### Issue: Experiment runs very slowly

**Diagnosis**:
```bash
# Check thread configuration
cat design/experiment/spec.txt | grep threads

# Monitor resource usage
top
```

**Solutions**:
- Increase `threads` in spec.txt (carefully, based on system resources)
- Reduce `num_run_cases` for testing
- Check network latency if using remote LLM services

### Issue: High memory usage

**Solutions**:
- Reduce concurrent threads
- Process cases in smaller batches
- Check for memory leaks in custom skillkits

## Configuration Issues

### Issue: Variables not taking effect

**Symptoms**: Agent doesn't use configured variable values.

**Diagnosis**:
```bash
# Check run_summary.yaml
cat env/experiment_*/run_001/run_summary.yaml

# Verify variable is in spec.txt
cat design/experiment/spec.txt | grep -A5 "variables:"
```

**Solution**:
- Ensure variable name matches exactly in both spec.txt and agent code
- Check that variable is in the `variables` section, not `configs`
- Verify sampling method is correct

### Issue: Config overrides not working

**Symptoms**: global.yaml changes don't take effect.

**Solution**:
```bash
# Check if override is in spec.txt
cat design/experiment/spec.txt | grep -A5 "configs:"

# Verify syntax (must be list format)
configs:
  - default: ["gpt-4"]  # Correct
  - default: "gpt-4"    # Wrong - must be list
```

## Debugging Tips

### Enable verbose logging

```bash
./bin/run --name experiment --verbose
```

This generates:
- Detailed per-case logs in `console/`
- Performance profiling in `profile/`

### Check execution history

```bash
# View case execution details
cat env/experiment_*/run_001/history/case_001.jsonl | jq .
```

### Replay a specific run

```bash
# Use generated replay script
bash env/experiment_*/run_001/cmds/replay.sh
```

### Inspect agent behavior

```bash
# View agent trajectory (if enabled)
cat env/experiment_*/run_001/trajectory/case_001.json | jq .
```

## Getting Help

If you're still stuck:

1. **Check logs**: Always start with `console/case_XXX.log`
2. **Verify configuration**: Double-check spec.txt and global.yaml
3. **Test in isolation**: Run with `num_run_cases: 1` to isolate issues
4. **Review documentation**: See [CLI Reference](../configuration/cli_reference.md) and [Analyst Guide](analyst_guide.md)

## Common Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| `Experiment not found` | Design directory doesn't exist | Check `design/` folder |
| `No runs found` | Experiment never executed | Run `./bin/run` first |
| `Benchmark not found` | Missing benchmark data | Check `benchmark/` directory |
| `Invalid spec.txt` | YAML syntax error | Validate YAML format |
| `Entrypoint not found` | .dph file missing | Check `dolphins/` folder |

## Related Documentation

- [Context Loader Debugging](context_loader_debugging.md) - Specific issues with Context Loader
- [Installation Guide](../quick_start/installation.md) - Setup and dependencies
- [CLI Reference](../configuration/cli_reference.md) - Command options
