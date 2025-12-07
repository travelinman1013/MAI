# Task: MLX-LM Provider - API Routes & Environment Config

**Project**: MLX-LM Provider
**Archon Project ID**: `503d952c-eedf-4252-ba71-1034a3430467`
**Sequence**: 4 of 5
**Depends On**: `03-provider-factory.md` completed (MLX-LM wired into providers.py)

---

## Archon Task Management

**Task ID**: `534d781a-bbde-4ac3-bb17-32f1419e8daa`

```bash
# Mark task as in-progress when starting
curl -X PUT "http://localhost:8181/api/tasks/534d781a-bbde-4ac3-bb17-32f1419e8daa" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark task as done when complete
curl -X PUT "http://localhost:8181/api/tasks/534d781a-bbde-4ac3-bb17-32f1419e8daa" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

With the provider factory updated, we now need to:
1. Expose MLX-LM in the API routes (`/models` endpoints)
2. Document configuration in `.env.example`

This makes MLX-LM fully usable through the API and properly documented for users.

---

## Requirements

### 1. Add MLX-LM Case to list_models Endpoint

**File**: `src/api/routes/models.py` (in `list_models` function, around line 103)

Add elif case for mlxlm after the llamacpp case:

```python
elif provider == "llamacpp":
    from src.infrastructure.llm.llamacpp_client import LlamaCppClient
    client = LlamaCppClient()
    raw_models = await client.list_models()
    for m in raw_models:
        models.append(ModelInfo(
            id=m.get("id", ""),
            name=m.get("id", ""),
            provider="llamacpp",
        ))

elif provider == "mlxlm":
    from src.infrastructure.llm.mlxlm_client import MlxLmClient
    client = MlxLmClient()
    raw_models = await client.list_models()
    for m in raw_models:
        models.append(ModelInfo(
            id=m.get("id", ""),
            name=m.get("id", ""),
            provider="mlxlm",
        ))

elif provider == "openai":
```

### 2. Add MLX-LM Case to get_loaded_models Endpoint

**File**: `src/api/routes/models.py` (in `get_loaded_models` function, around line 210)

Add elif case for mlxlm after the llamacpp case:

```python
elif provider == "llamacpp":
    from src.infrastructure.llm.llamacpp_client import LlamaCppClient
    client = LlamaCppClient()
    raw_models = await client.list_models()
    for m in raw_models:
        models.append(ModelInfo(
            id=m.get("id", ""),
            name=m.get("id", ""),
            provider="llamacpp",
        ))

elif provider == "mlxlm":
    from src.infrastructure.llm.mlxlm_client import MlxLmClient
    client = MlxLmClient()
    raw_models = await client.list_models()
    for m in raw_models:
        models.append(ModelInfo(
            id=m.get("id", ""),
            name=m.get("id", ""),
            provider="mlxlm",
        ))

elif provider == "openai":
```

### 3. Add MLX-LM to Health Check Endpoint

**File**: `src/api/routes/models.py` (in `check_provider_health` function, around line 336-345)

Add mlxlm import and to the health_fns dict:

```python
from src.core.models.lmstudio_provider import lmstudio_health_check
from src.core.models.ollama_provider import ollama_health_check
from src.core.models.llamacpp_provider import llamacpp_health_check
from src.core.models.mlxlm_provider import mlxlm_health_check

settings = get_settings()
provider = settings.llm.provider

health_fns = {
    "lmstudio": lmstudio_health_check,
    "ollama": ollama_health_check,
    "llamacpp": llamacpp_health_check,
    "mlxlm": mlxlm_health_check,
}
```

### 4. Add MLX-LM Configuration to .env.example

**File**: `.env.example` (after llama.cpp section, around line 135)

Add the MLX-LM configuration section:

```bash
# -----------------------------------------------------------------------------
# MLX-LM Configuration (when LLM__PROVIDER=mlxlm)
# -----------------------------------------------------------------------------
# MLX-LM runs on macOS host with Metal GPU acceleration.
# Install: pip install mlx-lm
# Run: mlx_lm.server --model mlx-community/Qwen2.5-1.5B-Instruct-4bit --port 8080
#
# Local development (host machine):
# MLXLM__BASE_URL=http://localhost:8080/v1
#
# Docker Compose (use host.docker.internal to reach host machine):
MLXLM__BASE_URL=http://host.docker.internal:8080/v1
MLXLM__API_KEY=not-needed
MLXLM__MODEL_NAME=local-model
MLXLM__MAX_TOKENS=2048
MLXLM__TEMPERATURE=0.7
MLXLM__TIMEOUT=120
```

### 5. Update LLM Provider Selection Comment

**File**: `.env.example` (around line 76-77)

Update the provider selection comment to include mlxlm:

```bash
# =============================================================================
# LLM Provider Configuration
# =============================================================================
# Provider selection: openai, lmstudio, ollama, llamacpp, mlxlm, or auto
# - auto: Tries to detect an available provider (OpenAI > LM Studio > Ollama > llama.cpp > MLX-LM)
LLM__PROVIDER=auto
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/api/routes/models.py` | Add mlxlm cases to list_models, get_loaded_models, check_provider_health |
| `.env.example` | Add MLX-LM configuration section, update provider comment |

---

## Success Criteria

```bash
# 1. API imports work
cd /Users/maxwell/Projects/MAI
python3 -c "from src.api.routes.models import list_models, get_loaded_models, check_provider_health; print('API imports OK')"
# Expected: API imports OK

# 2. .env.example contains MLX-LM section
grep -A5 "MLX-LM Configuration" .env.example
# Expected: Shows MLX-LM configuration section with comments

# 3. .env.example has updated provider list
grep "mlxlm" .env.example
# Expected: Shows lines mentioning mlxlm

# 4. Full API module loads without error
python3 -c "from src.api.routes import models; print('Full module loads OK')"
# Expected: Full module loads OK

# 5. Can run with mlxlm provider (doesn't need server)
LLM__PROVIDER=mlxlm python3 -c "
from src.core.utils.config import get_settings
s = get_settings()
print(f'mlxlm base_url: {s.mlxlm.base_url}')
print(f'provider: {s.llm.provider}')
"
# Expected:
# mlxlm base_url: http://localhost:8080/v1
# provider: mlxlm
```

---

## Technical Notes

### MLX-LM Server Quick Reference

```bash
# Install MLX-LM
pip install mlx-lm

# Run server with a model
mlx_lm.server --model mlx-community/Qwen2.5-1.5B-Instruct-4bit --port 8080

# Server options:
#   --model     : Model name from HuggingFace (required)
#   --port      : Server port (default: 8080)
#   --host      : Server host (default: 127.0.0.1)
#   --max-tokens: Max completion tokens (default: 512)
```

### Port Configuration Note

MLX-LM and llama.cpp both default to port 8080. Users running both should configure different ports:
- llama.cpp: Keep at 8080
- MLX-LM: Change to 8081 or another port

### Docker Access

When running the MAI API in Docker and MLX-LM on the host:
- Use `host.docker.internal` instead of `localhost`
- Example: `MLXLM__BASE_URL=http://host.docker.internal:8080/v1`

---

## On Completion

Mark task as done:
```bash
curl -X PUT "http://localhost:8181/api/tasks/534d781a-bbde-4ac3-bb17-32f1419e8daa" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

**Next Step**: Proceed to `05-unit-tests.md` to create comprehensive unit tests.
