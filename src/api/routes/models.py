"""API routes for LLM model management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.infrastructure.llm.lmstudio_client import lmstudio_client

router = APIRouter(prefix="/models", tags=["models"])


class ModelInfo(BaseModel):
    """Model information."""
    id: str
    name: str
    loaded: bool = False


class LoadModelRequest(BaseModel):
    """Request to load a model."""
    model_id: str


class ModelResponse(BaseModel):
    """Generic model operation response."""
    success: bool
    message: str
    model_id: str | None = None


@router.get("/", response_model=list[ModelInfo])
async def list_models() -> list[ModelInfo]:
    """List all available models from LM Studio."""
    try:
        models = await lmstudio_client.list_models()
        return [
            ModelInfo(
                id=m.get("id", "unknown"),
                name=m.get("id", "unknown").split("/")[-1],
                loaded=True,  # /v1/models returns loaded models
            )
            for m in models
        ]
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/loaded", response_model=list[ModelInfo])
async def get_loaded_models() -> list[ModelInfo]:
    """Get currently loaded models."""
    try:
        models = await lmstudio_client.get_loaded_models()
        return [
            ModelInfo(
                id=m.get("id", "unknown"),
                name=m.get("id", "unknown").split("/")[-1],
                loaded=True,
            )
            for m in models
        ]
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/load", response_model=ModelResponse)
async def load_model(request: LoadModelRequest) -> ModelResponse:
    """Load a model into LM Studio."""
    try:
        await lmstudio_client.load_model(request.model_id)
        return ModelResponse(
            success=True,
            message=f"Model {request.model_id} loaded successfully",
            model_id=request.model_id,
        )
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/unload", response_model=ModelResponse)
async def unload_model(request: LoadModelRequest) -> ModelResponse:
    """Unload a model from LM Studio."""
    try:
        await lmstudio_client.unload_model(request.model_id)
        return ModelResponse(
            success=True,
            message=f"Model {request.model_id} unloaded successfully",
            model_id=request.model_id,
        )
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
