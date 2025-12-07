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


class LoadModelRequest(BaseModel):
    """Request to load a model."""
    model_id: str


class ModelResponse(BaseModel):
    """Generic model operation response."""
    success: bool
    message: str
    model_id: Optional[str] = None


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


@router.get(
    "/loaded",
    response_model=List[ModelInfo],
    summary="Get loaded models",
    description="Get currently loaded models from the current provider."
)
async def get_loaded_models() -> List[ModelInfo]:
    """Get currently loaded models (backwards compatible endpoint)."""
    settings = get_settings()
    provider = settings.llm.provider

    if provider == "auto":
        from src.core.models.providers import _auto_detect_provider_async
        provider = await _auto_detect_provider_async()

    models = []

    try:
        if provider == "lmstudio":
            from src.infrastructure.llm.lmstudio_client import get_lmstudio_client
            raw_models = await get_lmstudio_client().get_loaded_models()
            for m in raw_models:
                models.append(ModelInfo(
                    id=m.get("id", "unknown"),
                    name=m.get("id", "unknown").split("/")[-1],
                    provider="lmstudio",
                ))

        elif provider == "ollama":
            from src.infrastructure.llm.ollama_client import OllamaClient
            client = OllamaClient()
            raw_models = await client.list_models()
            for m in raw_models:
                models.append(ModelInfo(
                    id=m.get("name", ""),
                    name=m.get("name", "").split(":")[0],
                    provider="ollama",
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

        elif provider == "openai":
            models.append(ModelInfo(
                id=settings.openai.model,
                name=settings.openai.model,
                provider="openai",
            ))

    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    return models


@router.post(
    "/load",
    response_model=ModelResponse,
    summary="Load a model",
    description="Load a model (LM Studio only)."
)
async def load_model(request: LoadModelRequest) -> ModelResponse:
    """Load a model into LM Studio."""
    settings = get_settings()

    if settings.llm.provider not in ("lmstudio", "auto"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model loading is only supported for LM Studio provider"
        )

    try:
        from src.infrastructure.llm.lmstudio_client import get_lmstudio_client
        await get_lmstudio_client().load_model(request.model_id)
        return ModelResponse(
            success=True,
            message=f"Model {request.model_id} loaded successfully",
            model_id=request.model_id,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post(
    "/unload",
    response_model=ModelResponse,
    summary="Unload a model",
    description="Unload a model (LM Studio only)."
)
async def unload_model(request: LoadModelRequest) -> ModelResponse:
    """Unload a model from LM Studio."""
    settings = get_settings()

    if settings.llm.provider not in ("lmstudio", "auto"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model unloading is only supported for LM Studio provider"
        )

    try:
        from src.infrastructure.llm.lmstudio_client import get_lmstudio_client
        await get_lmstudio_client().unload_model(request.model_id)
        return ModelResponse(
            success=True,
            message=f"Model {request.model_id} unloaded successfully",
            model_id=request.model_id,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


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
    provider = settings.llm.provider

    if provider == "auto":
        from src.core.models.providers import _auto_detect_provider_async
        provider = await _auto_detect_provider_async()

    if provider != "ollama":
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
                # Handle both dict and ProviderHealthStatus
                if isinstance(health, dict):
                    connected = health.get("connected", False)
                    model_id = health.get("model_id")
                    metadata = {k: v for k, v in health.items() if k not in ("connected", "model_id", "error")}
                else:
                    connected = health.connected
                    model_id = health.model_id
                    metadata = health.metadata if hasattr(health, 'metadata') else {}

                if connected:
                    return {
                        "provider": name,
                        "healthy": True,
                        "model": model_id,
                        "metadata": metadata,
                    }
            except Exception:
                continue
        return {"provider": "auto", "healthy": False, "error": "No providers available"}

    if provider in health_fns:
        try:
            health = await health_fns[provider]()
            # Handle both dict and ProviderHealthStatus
            if isinstance(health, dict):
                return {
                    "provider": provider,
                    "healthy": health.get("connected", False),
                    "model": health.get("model_id"),
                    "error": health.get("error"),
                    "metadata": {k: v for k, v in health.items() if k not in ("connected", "model_id", "error")},
                }
            else:
                return {
                    "provider": provider,
                    "healthy": health.connected,
                    "model": health.model_id,
                    "error": health.error,
                    "metadata": health.metadata if hasattr(health, 'metadata') else {},
                }
        except Exception as e:
            return {
                "provider": provider,
                "healthy": False,
                "error": str(e),
            }

    return {"provider": provider, "healthy": False, "error": "Unknown provider"}
