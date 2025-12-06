# 02 - LM Studio Model Switching

**Project**: MAI Frontend Enhancement
**Sequence**: 2 of 5
**Depends On**: 01-visual-theme-polish.md completed

---

## Archon Task Management

**Task ID**: `41d458c9-f026-407b-ae45-54020715dcec`
**Project ID**: `118ddd94-6aef-48cf-9397-43816f499907`

```bash
# Mark task as in-progress when starting
curl -X PUT "http://localhost:8181/api/tasks/41d458c9-f026-407b-ae45-54020715dcec" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Mark task as done when complete
curl -X PUT "http://localhost:8181/api/tasks/41d458c9-f026-407b-ae45-54020715dcec" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

---

## Context

LM Studio provides OpenAI-compatible APIs that allow programmatic model management. Currently, MAI uses a fixed model configured via environment variables. This task adds the ability to:
1. List available models from LM Studio
2. Switch between models from the UI
3. Load/unload models dynamically

The previous step (01) established a polished visual theme for the interface.

---

## Requirements

### 1. Create LM Studio Client Extensions

Create a new file `src/infrastructure/llm/lmstudio_client.py`:

```python
"""LM Studio API client for model management."""

import httpx
from typing import Any

from src.core.utils.config import settings


class LMStudioClient:
    """Client for LM Studio model management APIs."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.lm_studio.base_url.rstrip("/v1")
        # LM Studio management endpoints are at root, not /v1

    async def list_models(self) -> list[dict[str, Any]]:
        """List all available models in LM Studio.

        Returns:
            List of model objects with id, object, owned_by fields
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # OpenAI-compatible /v1/models endpoint
                response = await client.get(f"{self.base_url}/v1/models")
                response.raise_for_status()
                data = response.json()
                return data.get("data", [])
            except httpx.HTTPError as e:
                raise ConnectionError(f"Failed to list models: {e}") from e

    async def get_loaded_models(self) -> list[dict[str, Any]]:
        """Get currently loaded models.

        LM Studio's /v1/models returns only loaded models by default.
        """
        return await self.list_models()

    async def load_model(self, model_id: str) -> dict[str, Any]:
        """Load a model into memory.

        Args:
            model_id: The model identifier to load

        Returns:
            Load status response
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                # LM Studio REST API for loading models
                response = await client.post(
                    f"{self.base_url}/api/v0/models/load",
                    json={"model": model_id},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise ConnectionError(f"Failed to load model: {e}") from e

    async def unload_model(self, model_id: str) -> dict[str, Any]:
        """Unload a model from memory.

        Args:
            model_id: The model identifier to unload

        Returns:
            Unload status response
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/v0/models/unload",
                    json={"model": model_id},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise ConnectionError(f"Failed to unload model: {e}") from e


# Singleton instance
lmstudio_client = LMStudioClient()
```

### 2. Add API Endpoints for Model Management

Create or update `src/api/routes/models.py`:

```python
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
```

### 3. Register the Router

Update `src/api/routes/__init__.py` or `src/main.py` to include the models router:

```python
from src.api.routes.models import router as models_router

app.include_router(models_router, prefix="/api/v1")
```

### 4. Update GUI API Client

Add model management methods to `src/gui/api_client.py`:

```python
async def list_models(self) -> list[dict]:
    """List available models from LM Studio."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{self.base_url}/models/")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return []

async def load_model(self, model_id: str) -> dict:
    """Load a model in LM Studio."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{self.base_url}/models/load",
            json={"model_id": model_id},
        )
        response.raise_for_status()
        return response.json()

async def get_current_model(self) -> str | None:
    """Get the currently loaded model name."""
    models = await self.list_models()
    loaded = [m for m in models if m.get("loaded")]
    if loaded:
        return loaded[0].get("name")
    return None
```

### 5. Add Model Selector to GUI

Update `src/gui/app.py` to include a model selector:

```python
async def get_models_list() -> dict:
    """Fetch available models for dropdown."""
    try:
        models = await mai_client.list_models()
        if not models:
            return gr.Dropdown(choices=["No models available"], value="No models available")

        model_names = [m.get("id", "unknown") for m in models]
        # Select the first loaded model as default
        loaded = [m.get("id") for m in models if m.get("loaded")]
        default = loaded[0] if loaded else model_names[0]

        return gr.Dropdown(choices=model_names, value=default)
    except Exception:
        return gr.Dropdown(choices=["Error loading models"], value="Error loading models")


async def switch_model(model_id: str) -> str:
    """Switch to a different model."""
    if not model_id or model_id.startswith("No models") or model_id.startswith("Error"):
        return "No model selected"

    try:
        result = await mai_client.load_model(model_id)
        if result.get("success"):
            return f"Switched to {model_id}"
        return f"Failed: {result.get('message', 'Unknown error')}"
    except Exception as e:
        return f"Error: {e}"
```

Add the model selector to the interface:

```python
# In create_chat_interface(), add model selector row:
with gr.Row():
    with gr.Column(scale=2):
        agent_selector = gr.Dropdown(
            label="Agent",
            choices=[gui_settings.default_agent],
            value=gui_settings.default_agent,
            interactive=True,
        )
    with gr.Column(scale=2):
        model_selector = gr.Dropdown(
            label="Model",
            choices=["Loading..."],
            value="Loading...",
            interactive=True,
        )
    with gr.Column(scale=3):
        session_id = gr.Textbox(
            label="Session ID",
            value=initial_session_id,
            interactive=True,
        )
    with gr.Column(scale=1):
        with gr.Row():
            load_btn = gr.Button("Load", size="sm")
            new_btn = gr.Button("New", size="sm", variant="secondary")

# Model switch feedback
model_feedback = gr.Markdown("")

# Event handlers
demo.load(get_models_list, outputs=[model_selector])
model_selector.change(
    switch_model,
    inputs=[model_selector],
    outputs=[model_feedback],
)
```

---

## Files to Create/Modify

| Action | File Path |
|--------|-----------|
| CREATE | `src/infrastructure/llm/lmstudio_client.py` |
| CREATE | `src/api/routes/models.py` |
| MODIFY | `src/api/routes/__init__.py` or `src/main.py` |
| MODIFY | `src/gui/api_client.py` |
| MODIFY | `src/gui/app.py` |

---

## Success Criteria

```bash
# 1. Rebuild and restart services
docker compose up -d --build

# 2. Test API endpoint - list models
curl -s http://localhost:8000/api/v1/models/ | jq .
# Expected: Array of model objects with id, name, loaded fields

# 3. Test model loading (replace with actual model ID from LM Studio)
curl -s -X POST http://localhost:8000/api/v1/models/load \
  -H "Content-Type: application/json" \
  -d '{"model_id": "your-model-id"}' | jq .
# Expected: {"success": true, "message": "Model ... loaded successfully", ...}

# 4. GUI verification (manual)
# Open http://localhost:7860 and verify:
# - Model dropdown appears next to Agent selector
# - Dropdown populates with available models
# - Selecting a different model shows feedback message
# - Status bar updates with new model name

# 5. Check for errors
docker compose logs mai-api --tail=30 2>&1 | grep -i error
docker compose logs mai-gui --tail=30 2>&1 | grep -i error
# Expected: No errors related to model switching
```

---

## Technical Notes

- LM Studio's OpenAI-compatible endpoint `/v1/models` lists currently loaded models
- LM Studio REST API (beta) at `/api/v0/models/load` and `/api/v0/models/unload` handles model loading
- Model loading can take 30-120 seconds depending on model size
- LM Studio's "Auto-Evict" feature can automatically unload old models when loading new ones
- The timeout for load operations should be generous (120s+) for large models

**References**:
- [LM Studio OpenAI API](https://lmstudio.ai/docs/api/openai-api)
- [LM Studio REST API](https://lmstudio.ai/docs/api/rest-api)
- [Model Management Docs](https://lmstudio.ai/docs/python/manage-models/loading)

---

## On Completion

1. Mark Archon task as done:
```bash
curl -X PUT "http://localhost:8181/api/tasks/41d458c9-f026-407b-ae45-54020715dcec" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

2. Proceed to: `03-image-support.md`
