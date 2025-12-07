# Task: Extend Configuration for New Providers

**Project**: Flexible LLM Provider Support (`/Users/maxwell/Projects/MAI`)
**Goal**: Add OllamaSettings and LlamaCppSettings classes to the configuration system
**Sequence**: 2 of 10
**Depends On**: 01-provider-abstraction-layer.md

---

## Archon Task Management (REQUIRED)

This task is managed via Archon. Update status as you work.

### Task Info

- **Task ID**: `[TO_BE_ASSIGNED]`
- **Project ID**: `[TO_BE_ASSIGNED]`

### Update Status

```bash
# Mark as in_progress when starting
curl -X PUT "http://localhost:8181/api/tasks/[TASK_ID]" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark as done when complete
curl -X PUT "http://localhost:8181/api/tasks/[TASK_ID]" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

The previous task created the provider abstraction layer. Now we need to extend the configuration system to support the new Ollama and llama.cpp providers.

The configuration system uses Pydantic Settings with environment variable loading. Each provider has its own settings class with an environment prefix (e.g., `OLLAMA__BASE_URL`).

The existing `LMStudioSettings` class in `src/core/utils/config.py` serves as the pattern to follow.

---

## Requirements

### 1. Add OllamaSettings Class

Add a new settings class for Ollama configuration:

```python
class OllamaSettings(BaseSettings):
    """Ollama configuration.

    Environment variables use OLLAMA__ prefix.
    Example: OLLAMA__BASE_URL=http://localhost:11434/v1
    """

    model_config = SettingsConfigDict(
        env_prefix="OLLAMA__", env_nested_delimiter="__", extra="ignore"
    )

    base_url: str = Field(
        default="http://localhost:11434/v1",
        description="Base URL for Ollama API (OpenAI-compatible endpoint)",
    )
    api_key: str = Field(
        default="ollama",
        description="API key (Ollama accepts any value)",
    )
    model_name: str = Field(
        default="llama3.2",
        description="Default model to use",
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
        default=60,
        ge=1,
        description="Request timeout in seconds",
    )
    # Ollama-specific settings
    num_ctx: int = Field(
        default=4096,
        description="Context window size",
    )
    num_parallel: int = Field(
        default=2,
        description="Number of parallel requests Ollama can handle",
    )
```

### 2. Add LlamaCppSettings Class

Add a new settings class for llama.cpp server configuration:

```python
class LlamaCppSettings(BaseSettings):
    """llama.cpp server configuration.

    Environment variables use LLAMACPP__ prefix.
    Example: LLAMACPP__BASE_URL=http://localhost:8080/v1
    """

    model_config = SettingsConfigDict(
        env_prefix="LLAMACPP__", env_nested_delimiter="__", extra="ignore"
    )

    base_url: str = Field(
        default="http://localhost:8080/v1",
        description="Base URL for llama.cpp server (OpenAI-compatible endpoint)",
    )
    api_key: str = Field(
        default="not-needed",
        description="API key (not required for llama.cpp)",
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
        description="Request timeout in seconds (longer for large models)",
    )
    # llama.cpp-specific settings
    n_gpu_layers: int = Field(
        default=-1,
        description="Number of GPU layers (-1 for all available)",
    )
    ctx_size: int = Field(
        default=8192,
        description="Context window size",
    )
    n_threads: int = Field(
        default=4,
        description="Number of CPU threads to use",
    )
```

### 3. Update LLMProviderSettings

Extend the provider validator to accept the new providers:

```python
class LLMProviderSettings(BaseSettings):
    """LLM Provider selection configuration."""

    model_config = SettingsConfigDict(
        env_prefix="LLM__", env_nested_delimiter="__", extra="ignore"
    )

    provider: str = Field(
        default="auto",
        description="LLM provider to use: 'openai', 'lmstudio', 'ollama', 'llamacpp', or 'auto' (auto-detect)",
    )

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate provider selection."""
        allowed = {"openai", "lmstudio", "ollama", "llamacpp", "auto"}
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f"LLM provider must be one of {allowed}")
        return v_lower
```

### 4. Update Main Settings Class

Add the new settings as nested fields in the main Settings class:

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # Add these new nested settings alongside existing ones
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    llamacpp: LlamaCppSettings = Field(default_factory=LlamaCppSettings)
```

---

## Files to Modify

- `src/core/utils/config.py` - Add OllamaSettings, LlamaCppSettings, update LLMProviderSettings and Settings

---

## Success Criteria

```bash
# Verify new settings classes can be imported
python -c "from src.core.utils.config import OllamaSettings, LlamaCppSettings; print('Imports OK')"
# Expected: Imports OK

# Verify OllamaSettings defaults
python -c "from src.core.utils.config import OllamaSettings; s = OllamaSettings(); print(f'base_url={s.base_url}, model={s.model_name}')"
# Expected: base_url=http://localhost:11434/v1, model=llama3.2

# Verify LlamaCppSettings defaults
python -c "from src.core.utils.config import LlamaCppSettings; s = LlamaCppSettings(); print(f'base_url={s.base_url}, timeout={s.timeout}')"
# Expected: base_url=http://localhost:8080/v1, timeout=120

# Verify main Settings includes new providers
python -c "from src.core.utils.config import get_settings; s = get_settings(); print(f'ollama={s.ollama.base_url}, llamacpp={s.llamacpp.base_url}')"
# Expected: ollama=http://localhost:11434/v1, llamacpp=http://localhost:8080/v1

# Verify provider validator accepts new values
python -c "from src.core.utils.config import LLMProviderSettings; s = LLMProviderSettings(provider='ollama'); print(f'provider={s.provider}')"
# Expected: provider=ollama

# Verify invalid provider is rejected
python -c "from src.core.utils.config import LLMProviderSettings; LLMProviderSettings(provider='invalid')" 2>&1 | grep -q "must be one of" && echo "Validation works"
# Expected: Validation works
```

**Checklist:**
- [ ] OllamaSettings class added with all fields
- [ ] LlamaCppSettings class added with all fields
- [ ] LLMProviderSettings.validate_provider updated for new providers
- [ ] Settings class has ollama and llamacpp nested fields
- [ ] All environment variable prefixes are correct (OLLAMA__, LLAMACPP__)
- [ ] All imports work without errors

---

## Technical Notes

- **Existing Pattern**: Follow `LMStudioSettings` structure exactly
- **Environment Variables**: Double underscore (`__`) is used as nested delimiter
- **Defaults**: Ollama runs on port 11434, llama.cpp server typically on 8080
- **OpenAI Compatibility**: Both Ollama and llama.cpp expose `/v1/` endpoints
- **Timeout Values**: llama.cpp has longer default timeout (120s) as large models can be slower

---

## Important

- Do NOT remove or modify existing settings classes (OpenAISettings, LMStudioSettings)
- Ensure backward compatibility - existing configurations must continue to work
- Place new classes AFTER existing provider settings classes for consistency
- The Settings class field order should be: llm, openai, lm_studio, ollama, llamacpp, ...

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (03-ollama-provider.md) depends on this completing successfully
