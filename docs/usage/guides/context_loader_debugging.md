# Context Loader Debugging

Specific debugging guide for Context Loader runtime environment variable issues.

## Problem Description

Test script `demo/test_context_loader_connectivity.py` succeeds, but actual runtime (Dolphin agent) fails. Logs show using `"test"` as account ID instead of the configured UUID from environment variables.

## Problem Analysis

### Symptoms
- ✅ Test script: Uses correct `CONTEXT_LOADER_ACCOUNT_ID=2a4deda6-e481-11f0-b164-4a42a0df5a95`
- ❌ Runtime: Uses `"test"` as account ID
- ❌ Result: `query_object_instance` returns 500 error: `"user does not exist"`

### Root Cause

Runtime process (Dolphin) doesn't properly load environment variables. Possible reasons:

1. **Dolphin process doesn't inherit shell environment variables**
   - `~/.bashrc` only loads in interactive shells
   - Non-interactive processes (launched via scripts) don't automatically load `~/.bashrc`

2. **Environment variables not explicitly passed to child processes**
   - `bin/run` script may not explicitly pass environment variables
   - Child processes only inherit parent process environment variables

## Solutions

### Solution 1: Explicitly Set Environment Variables in Startup Script (Recommended)

Modify `bin/run` or startup script to set environment variables before starting Dolphin:

```python
# In bin/run's build_command function
import os

# Ensure environment variables are passed
env = os.environ.copy()
if "CONTEXT_LOADER_ACCOUNT_ID" not in env:
    # Try reading from ~/.bashrc
    bashrc_path = Path.home() / ".bashrc"
    if bashrc_path.exists():
        # Read and parse ~/.bashrc
        # Or set directly
        env["CONTEXT_LOADER_ACCOUNT_ID"] = "2a4deda6-e481-11f0-b164-4a42a0df5a95"
        env["CONTEXT_LOADER_ACCOUNT_TYPE"] = "user"
        env["CONTEXT_LOADER_BASE_URL"] = "http://192.168.167.13:30779"
        env["CONTEXT_LOADER_ACTION_INFO_BASE_URL"] = "http://192.168.167.13:8000"

# Use env in subprocess.run or subprocess.Popen
subprocess.run(cmd_parts, env=env)
```

### Solution 2: Use Configuration File (More Flexible)

Add environment variable configuration in `design/bird_baseline/config/global.yaml`:

```yaml
context_loader:
  account_id: "2a4deda6-e481-11f0-b164-4a42a0df5a95"
  account_type: "user"
  base_url: "http://192.168.167.13:30779"
  action_info_base_url: "http://192.168.167.13:8000"
```

Then prioritize reading from config file in skillkit.

### Solution 3: Add Fallback Mechanism in Skillkit

If environment variables aren't set, try reading from config file or default values:

```python
def _get_account_id(self) -> str:
    # 1. Check parameters
    if self._account_id:
        return self._account_id
    
    # 2. Check environment variables
    account_id = os.environ.get("CONTEXT_LOADER_ACCOUNT_ID", "").strip()
    if account_id:
        return account_id
    
    # 3. Check config file (if exists)
    # ... read config file
    
    # 4. Use default value (not recommended, but can be temporary solution)
    return "2a4deda6-e481-11f0-b164-4a42a0df5a95"
```

### Solution 4: Use .env File

Create `.env` file and load on startup:

```bash
# .env
CONTEXT_LOADER_ACCOUNT_ID=2a4deda6-e481-11f0-b164-4a42a0df5a95
CONTEXT_LOADER_ACCOUNT_TYPE=user
CONTEXT_LOADER_BASE_URL=http://192.168.167.13:30779
CONTEXT_LOADER_ACTION_INFO_BASE_URL=http://192.168.167.13:8000
```

In startup script:
```python
from dotenv import load_dotenv
load_dotenv()  # Load .env file
```

## Debugging Steps

### 1. Verify Environment Variables Are Passed

Add debug logging in skillkit:

```python
import logging
logger = logging.getLogger(__name__)

def _get_headers(self, ...):
    env_account_id = os.environ.get("CONTEXT_LOADER_ACCOUNT_ID", "")
    logger.warning(f"DEBUG: CONTEXT_LOADER_ACCOUNT_ID = {repr(env_account_id)}")
    logger.warning(f"DEBUG: All CONTEXT_LOADER_* env vars: {[k for k in os.environ.keys() if k.startswith('CONTEXT_LOADER_')]}")
```

### 2. Check Runtime Process Environment Variables

Add in `bin/run`:

```python
import os
print("DEBUG: Environment variables:")
for key in ["CONTEXT_LOADER_ACCOUNT_ID", "CONTEXT_LOADER_ACCOUNT_TYPE", "CONTEXT_LOADER_BASE_URL"]:
    print(f"  {key} = {repr(os.environ.get(key, 'NOT SET'))}")
```

### 3. Check Child Process Environment Variables

Print before starting Dolphin:

```python
cmd_parts = build_command(...)
print(f"DEBUG: Command: {' '.join(cmd_parts)}")
print(f"DEBUG: Environment: {dict((k, v) for k, v in os.environ.items() if 'CONTEXT_LOADER' in k)}")
```

## Temporary Solution

If you can't immediately modify startup script, add hardcoded fallback in skillkit:

```python
def _get_headers(self, ...):
    account_id = x_account_id or os.environ.get("CONTEXT_LOADER_ACCOUNT_ID", "").strip()
    
    # TEMPORARY FIX: Fallback to hardcoded value if env var not set
    if not account_id:
        account_id = "2a4deda6-e481-11f0-b164-4a42a0df5a95"
        import warnings
        warnings.warn("Using hardcoded CONTEXT_LOADER_ACCOUNT_ID. Please set environment variable!")
    
    # ... rest of the code
```

**Note**: This is only a temporary solution, should fix environment variable passing issue as soon as possible.

## Recommended Solution

**Prioritize Solution 1**: Explicitly set environment variables in startup script to ensure all child processes can access correct configuration.

This approach:
- ✅ Doesn't depend on shell configuration
- ✅ Centralized configuration management
- ✅ Easy to debug and maintain
- ✅ Works in all runtime environments

## Related Documentation

For general troubleshooting, see [Troubleshooting Guide](troubleshooting.md).
