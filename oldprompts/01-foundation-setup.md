# Task: MLX-LM Provider - Foundation Setup

**Project**: MLX-LM Provider
**Archon Project ID**: `503d952c-eedf-4252-ba71-1034a3430467`
**Sequence**: 1 of 5
**Depends On**: None (first step)

---

## Archon Task Management

**Task ID**: `cdb7dee3-9033-4b1d-af38-636c967761e7`

```bash
# Mark task as in-progress when starting
curl -X PUT "http://localhost:8181/api/tasks/cdb7dee3-9033-4b1d-af38-636c967761e7" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark task as done when complete
curl -X PUT "http://localhost:8181/api/tasks/cdb7dee3-9033-4b1d-af38-636c967761e7" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

We're adding MLX-LM as a new LLM provider for Apple Silicon Macs. MLX-LM is Apple's ML framework optimized for Metal GPU acceleration. The `mlx_lm.server` provides an OpenAI-compatible API.

This task establishes the foundation: configuration settings and the provider type enum.

---

## Requirements

### 1. Add MlxLmSettings Class to config.py

**File**: `src/core/utils/config.py`

Add a new settings class after `LlamaCppSettings` (around line 172):

```python
class MlxLmSettings(BaseSettings):
    """MLX-LM server configuration.

    Environment variables use MLXLM__ prefix.
    Example: MLXLM__BASE_URL=http://localhost:8080/v1

    MLX-LM runs on macOS host with Metal GPU acceleration.
    Server command: mlx_lm.server --model <model> --port 8080
    """

    model_config = SettingsConfigDict(
        env_prefix="MLXLM__", env_nested_delimiter="__", extra="ignore"
    )

    base_url: str = Field(
        default="http://localhost:8080/v1",
        description="Base URL for MLX-LM server (OpenAI-compatible endpoint)",
    )
    api_key: str = Field(
        default="not-needed",
        description="API key (not required for MLX-LM)",
    )
    model_name: str = Field(
        default="local-model",
        description="Model identifier (used for logging/display)",
    )
    max_tokens: int = Field(
        default=2048,
        description="Maximum tokens in response",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )
    timeout: int = Field(
        default=120,
        ge=1,
        description="Request timeout in seconds",
    )
```

### 2. Update LLMProviderSettings Validator

**File**: `src/core/utils/config.py` (line 33)

Update the `validate_provider` method to include "mlxlm":

```python
@field_validator("provider")
@classmethod
def validate_provider(cls, v: str) -> str:
    """Validate provider selection."""
    allowed = {"openai", "lmstudio", "ollama", "llamacpp", "mlxlm", "auto"}
    v_lower = v.lower()
    if v_lower not in allowed:
        raise ValueError(f"LLM provider must be one of {allowed}")
    return v_lower
```

### 3. Update provider description in LLMProviderSettings

**File**: `src/core/utils/config.py` (line 24-27)

Update the Field description:

```python
provider: str = Field(
    default="auto",
    description="LLM provider to use: 'openai', 'lmstudio', 'ollama', 'llamacpp', 'mlxlm', or 'auto' (auto-detect)",
)
```

### 4. Add mlxlm Field to Settings Class

**File**: `src/core/utils/config.py` (in the Settings class, around line 357)

Add alongside other provider settings:

```python
mlxlm: MlxLmSettings = Field(default_factory=MlxLmSettings)
```

### 5. Add MLXLM to ProviderType Enum

**File**: `src/core/models/base_provider.py` (line 34)

Add MLXLM to the enum:

```python
class ProviderType(str, Enum):
    """Supported LLM provider types.

    Each provider type represents a different LLM backend:
    - OPENAI: OpenAI API (GPT models)
    - LMSTUDIO: LM Studio local server (OpenAI-compatible)
    - OLLAMA: Ollama local model server
    - LLAMACPP: llama.cpp direct inference
    - MLXLM: MLX-LM server for Apple Silicon (Metal GPU)
    - AUTO: Automatic provider selection based on availability
    """

    OPENAI = "openai"
    LMSTUDIO = "lmstudio"
    OLLAMA = "ollama"
    LLAMACPP = "llamacpp"
    MLXLM = "mlxlm"
    AUTO = "auto"
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/core/utils/config.py` | Add MlxLmSettings class, update validator, add to Settings |
| `src/core/models/base_provider.py` | Add MLXLM to ProviderType enum |

---

## Success Criteria

```bash
# 1. Python imports work without error
cd /Users/maxwell/Projects/MAI
python3 -c "from src.core.utils.config import MlxLmSettings; print('MlxLmSettings imported')"
# Expected: MlxLmSettings imported

# 2. Settings class includes mlxlm
python3 -c "from src.core.utils.config import get_settings; s = get_settings(); print(f'mlxlm base_url: {s.mlxlm.base_url}')"
# Expected: mlxlm base_url: http://localhost:8080/v1

# 3. Validator accepts mlxlm
python3 -c "from src.core.utils.config import LLMProviderSettings; s = LLMProviderSettings(provider='mlxlm'); print(f'provider: {s.provider}')"
# Expected: provider: mlxlm

# 4. ProviderType enum includes MLXLM
python3 -c "from src.core.models.base_provider import ProviderType; print(ProviderType.MLXLM.value)"
# Expected: mlxlm

# 5. Environment variable override works
MLXLM__BASE_URL=http://custom:9999/v1 python3 -c "from src.core.utils.config import MlxLmSettings; s = MlxLmSettings(); print(f'base_url: {s.base_url}')"
# Expected: base_url: http://custom:9999/v1
```

---

## Technical Notes

- MLX-LM server default port is **8080** (same as llama.cpp, so users may want to change one)
- The server exposes `/health`, `/v1/models`, `/v1/chat/completions`, `/v1/completions`
- Default max tokens on server is 512, but we configure 2048 in settings for flexibility
- Temperature default on server is 0.0, we use 0.7 for more creative responses
- Follow the exact pattern used by `LlamaCppSettings` for consistency

---

## On Completion

Mark task as done:
```bash
curl -X PUT "http://localhost:8181/api/tasks/cdb7dee3-9033-4b1d-af38-636c967761e7" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

**Next Step**: Proceed to `02-core-implementation.md` to create the provider and client modules.
