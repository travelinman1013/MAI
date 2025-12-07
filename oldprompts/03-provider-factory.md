# Task: MLX-LM Provider - Provider Factory Integration

**Project**: MLX-LM Provider
**Archon Project ID**: `503d952c-eedf-4252-ba71-1034a3430467`
**Sequence**: 3 of 5
**Depends On**: `02-core-implementation.md` completed (mlxlm_provider.py and mlxlm_client.py exist)

---

## Archon Task Management

**Task ID**: `bbac7b71-57f2-460d-8516-4897f9d15ca2`

```bash
# Mark task as in-progress when starting
curl -X PUT "http://localhost:8181/api/tasks/bbac7b71-57f2-460d-8516-4897f9d15ca2" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark task as done when complete
curl -X PUT "http://localhost:8181/api/tasks/bbac7b71-57f2-460d-8516-4897f9d15ca2" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

With the provider module and client created, we now wire MLX-LM into the provider factory. This enables:
- `LLM__PROVIDER=mlxlm` configuration
- Auto-detection of MLX-LM as a fallback provider
- `get_model_provider()` and `get_model_provider_async()` support
- Health check aggregation via `check_all_providers()`

---

## Requirements

### 1. Add MLX-LM Imports

**File**: `src/core/models/providers.py` (top of file, after line 27)

Add imports for MLX-LM provider:

```python
from src.core.models.mlxlm_provider import (
    create_mlxlm_model,
    create_mlxlm_model_async,
    mlxlm_health_check,
)
```

### 2. Update ProviderType Literal

**File**: `src/core/models/providers.py` (line 34)

Update the type alias to include mlxlm:

```python
ProviderType = Literal["openai", "lmstudio", "ollama", "llamacpp", "mlxlm", "auto"]
```

### 3. Add MLX-LM to Auto-Detection

**File**: `src/core/models/providers.py` (in `_auto_detect_provider_async`, around line 85-89)

Add mlxlm to the local_providers list:

```python
# Try local providers in order
local_providers = [
    ("lmstudio", lmstudio_health_check),
    ("ollama", ollama_health_check),
    ("llamacpp", llamacpp_health_check),
    ("mlxlm", mlxlm_health_check),
]
```

### 4. Add MLX-LM Case to get_model_provider

**File**: `src/core/models/providers.py` (in `get_model_provider`, after llamacpp case around line 204)

Add elif case for mlxlm:

```python
elif selected_provider == "llamacpp":
    return create_llamacpp_model()
elif selected_provider == "mlxlm":
    return create_mlxlm_model()
else:
    raise ConfigurationError(
        f"Invalid LLM provider: {selected_provider}. "
        "Must be 'openai', 'lmstudio', 'ollama', 'llamacpp', 'mlxlm', or 'auto'."
    )
```

### 5. Add MLX-LM Case to get_model_provider_async

**File**: `src/core/models/providers.py` (in `get_model_provider_async`, after llamacpp case around line 276)

Add elif case for mlxlm:

```python
elif selected_provider == "llamacpp":
    return await create_llamacpp_model_async(
        auto_detect=auto_detect_model,
        test_connection=test_connection,
    )
elif selected_provider == "mlxlm":
    return await create_mlxlm_model_async(
        auto_detect=auto_detect_model,
        test_connection=test_connection,
    )
else:
    raise ConfigurationError(
        f"Invalid LLM provider: {selected_provider}. "
        "Must be 'openai', 'lmstudio', 'ollama', 'llamacpp', 'mlxlm', or 'auto'."
    )
```

### 6. Add MLX-LM to check_all_providers

**File**: `src/core/models/providers.py` (in `check_all_providers`, around line 319-323)

Add mlxlm to the health check loop:

```python
# Check local providers
for name, health_fn in [
    ("lmstudio", lmstudio_health_check),
    ("ollama", ollama_health_check),
    ("llamacpp", llamacpp_health_check),
    ("mlxlm", mlxlm_health_check),
]:
```

### 7. Update Docstrings and Comments

Update relevant docstrings to mention mlxlm:

**Module docstring** (line 1-6):
```python
"""LLM Provider Factory.

This module provides a unified factory for creating LLM model instances,
supporting multiple providers (OpenAI, LM Studio, Ollama, llama.cpp, MLX-LM)
with automatic selection and intelligent auto-detection.
"""
```

**get_model_provider docstring** (example section):
```python
# Force MLX-LM (Apple Silicon)
model = get_model_provider(provider="mlxlm")
```

**get_model_provider_async docstring** (description):
```python
"""Async version of get_model_provider with full auto-detection.

For local providers (LM Studio, Ollama, llama.cpp, MLX-LM), this can auto-detect
the loaded model and test the connection. For OpenAI, this behaves the
same as the sync version.
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/core/models/providers.py` | Add imports, update type, add to auto-detect, add cases to factory functions, update health checks |

---

## Success Criteria

```bash
# 1. Provider factory can create MLX-LM model
cd /Users/maxwell/Projects/MAI
python3 -c "from src.core.models.providers import get_model_provider; m = get_model_provider('mlxlm'); print(f'Created: {type(m).__name__}')"
# Expected: Created: OpenAIModel

# 2. Async factory works
python3 -c "
import asyncio
from src.core.models.providers import get_model_provider_async
async def test():
    m = await get_model_provider_async('mlxlm', test_connection=False)
    print(f'Created async: {type(m).__name__}')
asyncio.run(test())
"
# Expected: Created async: OpenAIModel

# 3. Auto-detection includes mlxlm in check
python3 -c "
import asyncio
from src.core.models.providers import check_all_providers
async def test():
    results = await check_all_providers()
    print('Providers checked:', list(results.keys()))
    assert 'mlxlm' in results
    print('mlxlm included: True')
asyncio.run(test())
"
# Expected:
# Providers checked: ['openai', 'lmstudio', 'ollama', 'llamacpp', 'mlxlm']
# mlxlm included: True

# 4. Environment variable selection works
LLM__PROVIDER=mlxlm python3 -c "
from src.core.utils.config import get_settings
from src.core.models.providers import get_model_provider
s = get_settings()
print(f'Provider setting: {s.llm.provider}')
m = get_model_provider()
print(f'Model created: {type(m).__name__}')
"
# Expected:
# Provider setting: mlxlm
# Model created: OpenAIModel

# 5. Invalid provider still raises error
python3 -c "
from src.core.models.providers import get_model_provider
try:
    get_model_provider('invalid')
except Exception as e:
    print(f'Error raised: {type(e).__name__}')
"
# Expected: Error raised: ConfigurationError
```

---

## Technical Notes

- MLX-LM is added **last** in the auto-detection order since it's newest and users likely have other providers configured
- The detection order is: OpenAI (if API key) > LM Studio > Ollama > llama.cpp > MLX-LM
- MLX-LM shares port 8080 with llama.cpp by default - users should configure different ports
- All error messages updated to include 'mlxlm' in the allowed list

---

## On Completion

Mark task as done:
```bash
curl -X PUT "http://localhost:8181/api/tasks/bbac7b71-57f2-460d-8516-4897f9d15ca2" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

**Next Step**: Proceed to `04-api-config.md` to update API routes and environment configuration.
