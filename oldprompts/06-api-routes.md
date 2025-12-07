# Task: Update API Routes for Multi-Provider Support

**Project**: Flexible LLM Provider Support (`/Users/maxwell/Projects/MAI`)
**Goal**: Update API endpoints to support multiple providers and add model management routes
**Sequence**: 6 of 10
**Depends On**: 05-provider-factory.md

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

The previous task updated the provider factory. Now we need to update the API layer to:
1. Return provider information in /llm-status endpoint
2. Add new /models endpoints for model management
3. Update response schemas

The existing `/llm-status` endpoint in `src/api/routes/agents.py` currently only checks LM Studio. We need to make it provider-aware.

---

## Requirements

### 1. Update LLMStatusResponse Schema

Update `src/api/schemas/agents.py`:

```python
from typing import List, Optional
from pydantic import BaseModel, Field


class LLMStatusResponse(BaseModel):
    """Response schema for LLM connection status."""

    provider: str = Field(..., description="Active LLM provider name")
    connected: bool = Field(..., description="Whether LLM provider is connected")
    model_name: Optional[str] = Field(None, description="Name of the loaded model")
    error: Optional[str] = Field(None, description="Error message if not connected")
    available_providers: Optional[List[str]] = Field(
        None, description="List of all configured provider names"
    )
    metadata: Optional[dict] = Field(
        None, description="Provider-specific metadata"
    )

    model_config = {"json_schema_extra": {"example": {
        "provider": "ollama",
        "connected": True,
        "model_name": "llama3.2:latest",
        "error": None,
        "available_providers": ["openai", "lmstudio", "ollama", "llamacpp"],
        "metadata": {"status": "ok"}
    }}}
```

### 2. Update get_llm_status Endpoint

Update `src/api/routes/agents.py`:

```python
@router.get(
    "/llm-status",
    response_model=LLMStatusResponse,
    summary="Get LLM connection status",
    description="Check if the LLM provider is connected and what model is loaded."
)
async def get_llm_status() -> LLMStatusResponse:
    """Check LLM provider connection status."""
    from src.core.utils.config import get_settings
    from src.core.models.lmstudio_provider import lmstudio_health_check
    from src.core.models.ollama_provider import ollama_health_check
    from src.core.models.llamacpp_provider import llamacpp_health_check

    settings = get_settings()
    provider = settings.llm.provider
    available_providers = ["openai", "lmstudio", "ollama", "llamacpp"]

    try:
        # Auto-detect active provider if set to auto
        if provider == "auto":
            # Try each provider
            for p_name, health_fn in [
                ("lmstudio", lmstudio_health_check),
                ("ollama", ollama_health_check),
                ("llamacpp", llamacpp_health_check),
            ]:
                try:
                    health = await health_fn()
                    if health.connected:
                        provider = p_name
                        return LLMStatusResponse(
                            provider=provider,
                            connected=True,
                            model_name=health.model_id,
                            available_providers=available_providers,
                            metadata=health.metadata,
                        )
                except Exception:
                    continue

            # Check OpenAI
            if settings.openai.api_key:
                return LLMStatusResponse(
                    provider="openai",
                    connected=True,
                    model_name=settings.openai.model,
                    available_providers=available_providers,
                )

            # Nothing available
            return LLMStatusResponse(
                provider="auto",
                connected=False,
                model_name=None,
                error="No providers available",
                available_providers=available_providers,
            )

        # Specific provider selected
        if provider == "openai":
            connected = bool(settings.openai.api_key)
            return LLMStatusResponse(
                provider=provider,
                connected=connected,
                model_name=settings.openai.model if connected else None,
                error=None if connected else "No API key configured",
                available_providers=available_providers,
            )

        elif provider == "lmstudio":
            health = await lmstudio_health_check()
        elif provider == "ollama":
            health = await ollama_health_check()
        elif provider == "llamacpp":
            health = await llamacpp_health_check()
        else:
            return LLMStatusResponse(
                provider=provider,
                connected=False,
                error=f"Unknown provider: {provider}",
                available_providers=available_providers,
            )

        return LLMStatusResponse(
            provider=provider,
            connected=health.connected,
            model_name=health.model_id,
            error=health.error,
            available_providers=available_providers,
            metadata=health.metadata,
        )

    except Exception as e:
        logger.error(f"Error checking LLM status: {e}")
        return LLMStatusResponse(
            provider=provider,
            connected=False,
            model_name=None,
            error=str(e),
            available_providers=available_providers,
        )
```

### 3. Create Models Route File

Create `src/api/routes/models.py`:

```python
"""Model management API routes.

Provides endpoints for listing models, checking provider health,
and managing models (pull/delete for Ollama).
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.core.utils.config import get_settings
from src.core.utils.logging import get_logger_with_context

logger = get_logger_with_context()

router = APIRouter(prefix="/models", tags=["models"])


class ModelInfo(BaseModel):
    """Model information."""
    id: str = Field(..., description="Model identifier")
    name: str = Field(..., description="Model display name")
    provider: str = Field(..., description="Provider this model is from")
    size: Optional[int] = Field(None, description="Model size in bytes")
    modified_at: Optional[str] = Field(None, description="Last modified timestamp")


class ProviderStatus(BaseModel):
    """Provider status information."""
    name: str = Field(..., description="Provider name")
    connected: bool = Field(..., description="Whether provider is connected")
    model: Optional[str] = Field(None, description="Currently loaded model")
    error: Optional[str] = Field(None, description="Error message if any")
    base_url: Optional[str] = Field(None, description="Provider base URL")


class ModelsListResponse(BaseModel):
    """Response for list models endpoint."""
    models: List[ModelInfo] = Field(default_factory=list)
    provider: str = Field(..., description="Provider the models are from")


class ProvidersListResponse(BaseModel):
    """Response for list providers endpoint."""
    providers: List[ProviderStatus] = Field(default_factory=list)
    active_provider: str = Field(..., description="Currently configured provider")


@router.get(
    "/",
    response_model=ModelsListResponse,
    summary="List available models",
    description="List all available models from the current provider."
)
async def list_models() -> ModelsListResponse:
    """List available models from the current provider."""
    settings = get_settings()
    provider = settings.llm.provider

    if provider == "auto":
        # Try to find an active provider
        from src.core.models.providers import _auto_detect_provider_async
        provider = await _auto_detect_provider_async()

    models = []

    try:
        if provider == "ollama":
            from src.infrastructure.llm.ollama_client import OllamaClient
            client = OllamaClient()
            raw_models = await client.list_models()
            for m in raw_models:
                models.append(ModelInfo(
                    id=m.get("name", ""),
                    name=m.get("name", "").split(":")[0],
                    provider="ollama",
                    size=m.get("size"),
                    modified_at=m.get("modified_at"),
                ))

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

        elif provider == "lmstudio":
            from src.core.models.lmstudio_provider import detect_lmstudio_model
            model_id = await detect_lmstudio_model(settings.lm_studio.base_url)
            if model_id:
                models.append(ModelInfo(
                    id=model_id,
                    name=model_id,
                    provider="lmstudio",
                ))

        elif provider == "openai":
            # Just return configured model
            models.append(ModelInfo(
                id=settings.openai.model,
                name=settings.openai.model,
                provider="openai",
            ))

    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to list models: {str(e)}"
        )

    return ModelsListResponse(models=models, provider=provider)


@router.get(
    "/providers",
    response_model=ProvidersListResponse,
    summary="List providers",
    description="List all available LLM providers and their status."
)
async def list_providers() -> ProvidersListResponse:
    """List available LLM providers and their connection status."""
    from src.core.models.providers import check_all_providers

    settings = get_settings()
    health_results = await check_all_providers()

    providers = []
    for name, health in health_results.items():
        providers.append(ProviderStatus(
            name=name,
            connected=health.connected,
            model=health.model_id,
            error=health.error,
            base_url=health.base_url if health.base_url else None,
        ))

    return ProvidersListResponse(
        providers=providers,
        active_provider=settings.llm.provider,
    )


@router.post(
    "/pull/{model_name:path}",
    summary="Pull a model",
    description="Pull a model from the registry (Ollama only)."
)
async def pull_model(model_name: str):
    """Pull a model (Ollama only).

    Args:
        model_name: Name of model to pull (e.g., "llama3.2", "codellama:7b")
    """
    settings = get_settings()

    if settings.llm.provider != "ollama":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model pulling is only supported for Ollama provider"
        )

    from src.infrastructure.llm.ollama_client import OllamaClient
    client = OllamaClient()

    try:
        # Start pull and collect progress
        progress_updates = []
        async for update in client.pull_model(model_name):
            progress_updates.append(update)

        return {
            "status": "success",
            "model": model_name,
            "message": f"Model {model_name} pulled successfully"
        }

    except Exception as e:
        logger.error(f"Error pulling model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pull model: {str(e)}"
        )


@router.get(
    "/health",
    summary="Check provider health",
    description="Check health of the current LLM provider."
)
async def check_provider_health():
    """Check health of current provider."""
    from src.core.models.lmstudio_provider import lmstudio_health_check
    from src.core.models.ollama_provider import ollama_health_check
    from src.core.models.llamacpp_provider import llamacpp_health_check

    settings = get_settings()
    provider = settings.llm.provider

    health_fns = {
        "lmstudio": lmstudio_health_check,
        "ollama": ollama_health_check,
        "llamacpp": llamacpp_health_check,
    }

    if provider == "openai":
        return {
            "provider": "openai",
            "healthy": bool(settings.openai.api_key),
            "model": settings.openai.model,
        }

    if provider == "auto":
        # Return health of first available
        for name, fn in health_fns.items():
            try:
                health = await fn()
                if health.connected:
                    return {
                        "provider": name,
                        "healthy": True,
                        "model": health.model_id,
                        "metadata": health.metadata,
                    }
            except Exception:
                continue
        return {"provider": "auto", "healthy": False, "error": "No providers available"}

    if provider in health_fns:
        try:
            health = await health_fns[provider]()
            return {
                "provider": provider,
                "healthy": health.connected,
                "model": health.model_id,
                "error": health.error,
                "metadata": health.metadata,
            }
        except Exception as e:
            return {
                "provider": provider,
                "healthy": False,
                "error": str(e),
            }

    return {"provider": provider, "healthy": False, "error": "Unknown provider"}
```

### 4. Register New Router

Update `src/api/main.py` to include the new router:

```python
from src.api.routes.models import router as models_router

# Add with other router includes
app.include_router(models_router, prefix="/api")
```

---

## Files to Create

- `src/api/routes/models.py` - New model management routes

## Files to Modify

- `src/api/schemas/agents.py` - Update LLMStatusResponse
- `src/api/routes/agents.py` - Update get_llm_status endpoint
- `src/api/main.py` - Register new models router

---

## Success Criteria

```bash
# Verify models router imports
python -c "from src.api.routes.models import router; print('Router OK')"
# Expected: Router OK

# Verify updated schema
python -c "from src.api.schemas.agents import LLMStatusResponse; r = LLMStatusResponse(provider='test', connected=True); print(r.available_providers)"
# Expected: None

# Start the API and test endpoints (if server can start)
# curl http://localhost:8000/api/llm-status
# curl http://localhost:8000/api/models/
# curl http://localhost:8000/api/models/providers
# curl http://localhost:8000/api/models/health
```

**Checklist:**
- [ ] LLMStatusResponse updated with new fields
- [ ] get_llm_status handles all providers
- [ ] models.py router created with all endpoints
- [ ] /models/ endpoint lists models
- [ ] /models/providers endpoint lists all providers
- [ ] /models/pull/{name} works for Ollama
- [ ] /models/health checks current provider
- [ ] Router registered in main.py

---

## Technical Notes

- **Path Parameter**: Use `{model_name:path}` to allow slashes in model names (e.g., "library/model")
- **Provider Import**: Import health check functions inside endpoint to avoid circular imports
- **Error Handling**: Return 503 for service unavailable, 400 for bad requests
- **Auto Mode**: When provider is "auto", try to find and use an active provider

---

## Important

- Do NOT break existing /llm-status behavior for LM Studio users
- All new fields in response schemas should be Optional
- Handle cases where no providers are available gracefully
- Model pull is long-running - consider async/streaming response in future

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (07-docker-integration.md) depends on this completing successfully
