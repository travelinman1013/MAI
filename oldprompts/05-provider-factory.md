# Task: Update Provider Factory

**Project**: Flexible LLM Provider Support (`/Users/maxwell/Projects/MAI`)
**Goal**: Update the provider factory to support all providers with auto-detection logic
**Sequence**: 5 of 10
**Depends On**: 04-llamacpp-provider.md

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

The previous tasks implemented individual providers for Ollama and llama.cpp. Now we need to update the central provider factory (`src/core/models/providers.py`) to support all providers and implement intelligent auto-detection.

The factory provides a unified interface for creating LLM model instances regardless of the underlying provider. When `provider="auto"`, it tries each provider in order until one succeeds.

---

## Requirements

### 1. Review Existing Provider Factory

First, read the existing `src/core/models/providers.py` to understand the current structure.

### 2. Update Provider Type Definition

Update or add the ProviderType literal:

```python
from typing import Literal, Optional

ProviderType = Literal["openai", "lmstudio", "ollama", "llamacpp", "auto"]
```

### 3. Add New Provider Imports

Add imports for the new providers:

```python
from src.core.models.lmstudio_provider import (
    create_lmstudio_model,
    create_lmstudio_model_async,
    lmstudio_health_check,
)
from src.core.models.ollama_provider import (
    create_ollama_model,
    create_ollama_model_async,
    ollama_health_check,
)
from src.core.models.llamacpp_provider import (
    create_llamacpp_model,
    create_llamacpp_model_async,
    llamacpp_health_check,
)
```

### 4. Implement Auto-Detection Logic

Create functions to auto-detect which provider to use:

```python
async def _auto_detect_provider_async() -> str:
    """Async auto-detection with connectivity checks.

    Tries providers in this order:
    1. OpenAI if API key is configured
    2. LM Studio
    3. Ollama
    4. llama.cpp

    Returns:
        Provider name string
    """
    settings = get_settings()

    # Check OpenAI first if API key is set
    if settings.openai.api_key:
        logger.info("Auto-detect: Using OpenAI (API key configured)")
        return "openai"

    # Try local providers in order
    local_providers = [
        ("lmstudio", lmstudio_health_check),
        ("ollama", ollama_health_check),
        ("llamacpp", llamacpp_health_check),
    ]

    for provider_name, health_check_fn in local_providers:
        try:
            health = await health_check_fn()
            if health.connected:
                logger.info(
                    f"Auto-detect: Using {provider_name}",
                    model=health.model_id,
                )
                return provider_name
        except Exception as e:
            logger.debug(f"Auto-detect: {provider_name} not available: {e}")
            continue

    # Default to lmstudio if nothing else works
    logger.warning("Auto-detect: No providers available, defaulting to lmstudio")
    return "lmstudio"


def _auto_detect_provider() -> str:
    """Sync auto-detection (limited - prefers configured provider).

    For full auto-detection with connectivity checks, use async version.

    Returns:
        Provider name string
    """
    settings = get_settings()

    # Check OpenAI first if API key is set
    if settings.openai.api_key:
        return "openai"

    # In sync context, just return configured or default
    return settings.llm.provider if settings.llm.provider != "auto" else "lmstudio"
```

### 5. Update get_model_provider Function

Update the main factory function:

```python
def get_model_provider(
    provider: Optional[ProviderType] = None,
) -> OpenAIModel:
    """Get an LLM model instance based on provider configuration.

    Args:
        provider: Provider to use. If None, uses configured provider.
                  If "auto", attempts auto-detection.

    Returns:
        Configured OpenAIModel instance

    Raises:
        ConfigurationError: If provider is invalid or unavailable
    """
    settings = get_settings()
    selected_provider = provider or settings.llm.provider

    if selected_provider == "auto":
        selected_provider = _auto_detect_provider()

    logger.info(f"Creating model for provider: {selected_provider}")

    if selected_provider == "openai":
        from pydantic_ai.models.openai import OpenAIModel
        return OpenAIModel(
            settings.openai.model,
            api_key=settings.openai.api_key,
        )
    elif selected_provider == "lmstudio":
        return create_lmstudio_model()
    elif selected_provider == "ollama":
        return create_ollama_model()
    elif selected_provider == "llamacpp":
        return create_llamacpp_model()
    else:
        raise ConfigurationError(
            f"Invalid LLM provider: {selected_provider}. "
            "Must be 'openai', 'lmstudio', 'ollama', 'llamacpp', or 'auto'."
        )
```

### 6. Add Async Factory Function

Add async version with full auto-detection:

```python
async def get_model_provider_async(
    provider: Optional[ProviderType] = None,
    test_connection: bool = False,
    auto_detect_model: bool = True,
) -> OpenAIModel:
    """Async version of get_model_provider with full auto-detection.

    Args:
        provider: Provider to use. If None, uses configured provider.
        test_connection: If True, verify connection before returning.
        auto_detect_model: If True, auto-detect model from provider.

    Returns:
        Configured OpenAIModel instance

    Raises:
        ConfigurationError: If provider is invalid
        ModelError: If connection test fails
    """
    settings = get_settings()
    selected_provider = provider or settings.llm.provider

    if selected_provider == "auto":
        selected_provider = await _auto_detect_provider_async()

    logger.info(f"Creating async model for provider: {selected_provider}")

    if selected_provider == "openai":
        from pydantic_ai.models.openai import OpenAIModel
        model = OpenAIModel(
            settings.openai.model,
            api_key=settings.openai.api_key,
        )
        return model
    elif selected_provider == "lmstudio":
        return await create_lmstudio_model_async(
            auto_detect=auto_detect_model,
            test_connection=test_connection,
        )
    elif selected_provider == "ollama":
        return await create_ollama_model_async(
            auto_detect=auto_detect_model,
            test_connection=test_connection,
        )
    elif selected_provider == "llamacpp":
        return await create_llamacpp_model_async(
            auto_detect=auto_detect_model,
            test_connection=test_connection,
        )
    else:
        raise ConfigurationError(
            f"Invalid LLM provider: {selected_provider}. "
            "Must be 'openai', 'lmstudio', 'ollama', 'llamacpp', or 'auto'."
        )
```

### 7. Add Health Check Helper

Add a unified health check function:

```python
async def check_all_providers() -> dict[str, ProviderHealthStatus]:
    """Check health of all configured providers.

    Returns:
        Dict mapping provider name to health status
    """
    from src.core.models.base_provider import ProviderHealthStatus

    results = {}

    # Check OpenAI (just config validation)
    settings = get_settings()
    results["openai"] = ProviderHealthStatus(
        connected=bool(settings.openai.api_key),
        model_detected=bool(settings.openai.api_key),
        model_id=settings.openai.model if settings.openai.api_key else None,
        base_url="https://api.openai.com/v1",
        provider_type="openai",
    )

    # Check local providers
    for name, health_fn in [
        ("lmstudio", lmstudio_health_check),
        ("ollama", ollama_health_check),
        ("llamacpp", llamacpp_health_check),
    ]:
        try:
            results[name] = await health_fn()
        except Exception as e:
            results[name] = ProviderHealthStatus(
                connected=False,
                model_detected=False,
                model_id=None,
                base_url="",
                error=str(e),
                provider_type=name,
            )

    return results
```

---

## Files to Modify

- `src/core/models/providers.py` - Update factory with new providers and auto-detection

---

## Success Criteria

```bash
# Verify imports work
python -c "from src.core.models.providers import get_model_provider, get_model_provider_async; print('Imports OK')"
# Expected: Imports OK

# Verify sync factory with explicit provider
python -c "from src.core.models.providers import get_model_provider; m = get_model_provider('lmstudio'); print(type(m).__name__)"
# Expected: OpenAIModel

# Verify sync factory with ollama
python -c "from src.core.models.providers import get_model_provider; m = get_model_provider('ollama'); print(type(m).__name__)"
# Expected: OpenAIModel

# Verify sync factory with llamacpp
python -c "from src.core.models.providers import get_model_provider; m = get_model_provider('llamacpp'); print(type(m).__name__)"
# Expected: OpenAIModel

# Verify invalid provider raises error
python -c "from src.core.models.providers import get_model_provider; get_model_provider('invalid')" 2>&1 | grep -q "Invalid LLM provider" && echo "Validation works"
# Expected: Validation works

# Verify check_all_providers
python -c "
import asyncio
from src.core.models.providers import check_all_providers
results = asyncio.run(check_all_providers())
print(f'Providers checked: {list(results.keys())}')
"
# Expected: Providers checked: ['openai', 'lmstudio', 'ollama', 'llamacpp']
```

**Checklist:**
- [ ] New provider imports added
- [ ] ProviderType updated with all providers
- [ ] _auto_detect_provider sync function implemented
- [ ] _auto_detect_provider_async function implemented
- [ ] get_model_provider handles all providers
- [ ] get_model_provider_async implemented
- [ ] check_all_providers helper added
- [ ] All providers work in factory

---

## Technical Notes

- **Auto-Detection Order**: OpenAI (if key) > LM Studio > Ollama > llama.cpp
- **Sync vs Async**: Sync auto-detect can't do connectivity checks; async can
- **Import Location**: OpenAI import is inline to avoid circular imports
- **Error Handling**: Use ConfigurationError for invalid providers, ModelError for connection issues

---

## Important

- Do NOT break backward compatibility - existing LM Studio usage must work
- Auto-detect should silently try providers without raising errors
- The sync version should work even if no providers are running
- Log the selected provider for debugging

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (06-api-routes.md) depends on this completing successfully
