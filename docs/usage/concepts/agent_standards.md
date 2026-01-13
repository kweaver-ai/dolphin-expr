# Agent Development Standards

Note: For rules that actually apply to Codex/agents, refer to `AGENTS.md` in the repository root; this document serves as supplementary documentation.

## Code Style Requirements

### 1. Comments
- **All code comments MUST be written in English**
- Use clear, concise English for inline comments, docstrings, and documentation
- Follow standard Python docstring conventions (Google or NumPy style)

Example:
```python
def run_benchmark(benchmark_name: str, num_cases: int):
    """
    Run benchmark test with specified number of cases.

    Args:
        benchmark_name: Name of the benchmark to run
        num_cases: Number of test cases to execute

    Returns:
        Dictionary containing test results and metrics
    """
    # Initialize benchmark configuration
    config = load_benchmark_config(benchmark_name)

    # Execute test cases in parallel
    results = execute_parallel(config, num_cases)

    return results
```

### 2. Logging
- **All new log messages MUST be written in English**
- Use appropriate log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Include context information in log messages

Example:
```python
logger.info("Starting experiment: %s", experiment_name)
logger.debug("Configuration loaded: %d parameters", len(config))
logger.warning("Missing optional parameter: %s, using default", param_name)
logger.error("Failed to load benchmark data: %s", error_message)
```

### 3. Exception Messages
- All exception messages should be in English
- Provide clear, actionable error descriptions

Example:
```python
raise ValueError(f"Invalid benchmark name: {name}. Expected one of: {valid_names}")
raise FileNotFoundError(f"Benchmark data not found at: {path}")
```

## Project-Specific Guidelines

### Experiment System Development

1. **File Naming**
   - Use snake_case for Python files: `experiment_runner.py`
   - Use kebab-case for config files: `global-config.yaml`
   - Use descriptive names that reflect functionality

2. **Module Organization**
   - Keep experiment logic in `bin/` scripts
   - Analysis tools in `analyst/` directory
   - Benchmark data in `benchmark/` directory
   - Experiment designs in `design/` directory

3. **Configuration Management**
   - Use YAML for configuration files
   - Document all configuration options
   - Provide sensible defaults

4. **Logging Best Practices**
   - Log experiment start/end with timestamps
   - Log configuration changes
   - Log error details for debugging
   - Use structured logging when possible

Example:
```python
logger.info("Experiment started: name=%s, timestamp=%s", exp_name, timestamp)
logger.info("Configuration: model=%s, num_cases=%d, threads=%d",
            model, num_cases, threads)
logger.error("Experiment failed: name=%s, error=%s, traceback=%s",
             exp_name, str(error), traceback.format_exc())
```

## Commit Message Guidelines

- Use English for commit messages
- Follow conventional commit format:
  - `feat:` for new features
  - `fix:` for bug fixes
  - `docs:` for documentation changes
  - `refactor:` for code refactoring
  - `test:` for test additions/changes

Example:
```
feat: add parallel execution support for benchmark tests

- Implement ThreadPoolExecutor for concurrent test execution
- Add configurable thread count in spec.txt
- Update logging to track individual case progress

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

## Documentation Requirements

### Code Documentation
- All public functions/classes must have docstrings
- Document parameters, return values, and exceptions
- Include usage examples for complex functions

### User-Facing Documentation
- README files can be in Chinese for user convenience
- Technical documentation (this file) should be in English
- API documentation must be in English

## Internationalization Notes

- **Code layer**: English only (comments, logs, exceptions)
- **User interface**: Can use Chinese (CLI help messages, user prompts)
- **Documentation**:
  - Technical docs: English
  - User guides: Chinese preferred for Chinese-speaking users
  - Comments in code: English only

## Enforcement

- Code reviews should check for English comments and logs
- CI/CD (if added) should validate commit message format
- Linters should be configured to accept English comments

## Migration Strategy

For existing code with Chinese comments/logs:
1. **Priority**: Update new code first
2. **Gradual migration**: Update old code when modifying it
3. **No breaking changes**: Keep existing functionality while improving code quality

## Questions?

If you're unsure about any style requirements, refer to:
- PEP 8 for Python code style
- Google Python Style Guide for docstrings
- Conventional Commits for commit messages
