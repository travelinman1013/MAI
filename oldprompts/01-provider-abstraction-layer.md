# Task: Create Provider Abstraction Layer

**Project**: Flexible LLM Provider Support (`/Users/maxwell/Projects/MAI`)
**Goal**: Create base provider protocol and types that all LLM providers must implement
**Sequence**: 1 of 10
**Depends On**: None (first step)

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

The MAI framework currently supports LM Studio as its local LLM provider via `src/core/models/lmstudio_provider.py`. We are extending this to support multiple providers (Ollama, llama.cpp) in addition to the existing LM Studio and OpenAI options.

This first task creates the abstraction layer that defines what all LLM providers must implement. This ensures consistent behavior across providers and makes it easy to add new ones in the future.

The abstraction uses a Protocol (structural typing) rather than abstract base class, following Python's duck-typing philosophy while still providing clear interface documentation.

---

## Requirements

### 1. Create ProviderType Enum

Define an enum for all supported provider types:

```python
from enum import Enum

class ProviderType(str, Enum):
    """Supported LLM provider types."""
    OPENAI = "openai"
    LMSTUDIO = "lmstudio"
    OLLAMA = "ollama"
    LLAMACPP = "llamacpp"
    AUTO = "auto"
```

### 2. Create ProviderHealthStatus Dataclass

Define a dataclass to standardize health check responses across all providers:

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ProviderHealthStatus:
    """Standardized health check result for LLM providers."""
    connected: bool
    model_detected: bool
    model_id: Optional[str]
    base_url: str
    error: Optional[str] = None
    provider_type: Optional[str] = None
    metadata: dict = field(default_factory=dict)
```

### 3. Create LLMProviderProtocol

Define the Protocol that all providers must implement:

```python
from typing import Protocol, Optional, Any

class LLMProviderProtocol(Protocol):
    """Protocol defining the interface all LLM providers must implement.

    This protocol uses structural typing - any class that implements these
    methods is considered a valid provider, without explicit inheritance.
    """

    async def health_check(self) -> ProviderHealthStatus:
        """Perform health check on the provider.

        Returns:
            ProviderHealthStatus with connection and model information
        """
        ...

    async def list_models(self) -> list[dict[str, Any]]:
        """List available models from this provider.

        Returns:
            List of model information dictionaries
        """
        ...

    async def detect_model(self) -> Optional[str]:
        """Detect the currently loaded/default model.

        Returns:
            Model ID string or None if no model detected
        """
        ...

    def create_model(self, model_name: Optional[str] = None) -> Any:
        """Create a model instance synchronously.

        Args:
            model_name: Optional model name override

        Returns:
            Configured model instance (typically OpenAIModel)
        """
        ...

    async def create_model_async(
        self,
        model_name: Optional[str] = None,
        auto_detect: bool = True,
        test_connection: bool = True,
    ) -> Any:
        """Create a model instance asynchronously with auto-detection.

        Args:
            model_name: Optional model name override
            auto_detect: If True, detect model from provider
            test_connection: If True, verify connection before returning

        Returns:
            Configured model instance (typically OpenAIModel)
        """
        ...
```

### 4. Update Module Exports

Update `src/core/models/__init__.py` to export the new types:

```python
from src.core.models.base_provider import (
    ProviderType,
    ProviderHealthStatus,
    LLMProviderProtocol,
)
```

---

## Files to Create

- `src/core/models/base_provider.py` - Provider abstraction with ProviderType, ProviderHealthStatus, and LLMProviderProtocol

## Files to Modify

- `src/core/models/__init__.py` - Add exports for new base provider types

---

## Success Criteria

```bash
# Verify the file was created with correct structure
python -c "from src.core.models.base_provider import ProviderType, ProviderHealthStatus, LLMProviderProtocol; print('Imports OK')"
# Expected: Imports OK

# Verify ProviderType enum values
python -c "from src.core.models.base_provider import ProviderType; print([p.value for p in ProviderType])"
# Expected: ['openai', 'lmstudio', 'ollama', 'llamacpp', 'auto']

# Verify ProviderHealthStatus can be instantiated
python -c "from src.core.models.base_provider import ProviderHealthStatus; h = ProviderHealthStatus(connected=True, model_detected=True, model_id='test', base_url='http://localhost'); print(h)"
# Expected: ProviderHealthStatus(connected=True, model_detected=True, model_id='test', base_url='http://localhost', error=None, provider_type=None, metadata={})

# Verify exports from models package
python -c "from src.core.models import ProviderType, ProviderHealthStatus; print('Package exports OK')"
# Expected: Package exports OK
```

**Checklist:**
- [ ] `base_provider.py` created with all three types
- [ ] ProviderType enum has all 5 values
- [ ] ProviderHealthStatus is a proper dataclass with defaults
- [ ] LLMProviderProtocol defines all 5 required methods
- [ ] Module `__init__.py` exports the new types
- [ ] All imports work without errors

---

## Technical Notes

- **Pattern Reference**: Follow the structure of `src/core/models/lmstudio_provider.py` for style and conventions
- **Type Hints**: Use `from __future__ import annotations` for forward references if needed
- **Protocol vs ABC**: We use Protocol for structural typing - this means existing providers don't need to explicitly inherit from it
- **Dataclass vs Pydantic**: Use dataclass for ProviderHealthStatus since it's a simple data container, not a settings model

---

## Important

- Do NOT modify `lmstudio_provider.py` in this step - we will refactor it later to use the new types
- The Protocol is for documentation and type checking purposes - we won't enforce runtime checks
- Keep the module focused only on type definitions - no implementation logic

---

## On Completion

1. Mark Archon task as `done` using the command above
2. Verify ALL success criteria pass
3. The next task (02-configuration-extension.md) depends on this completing successfully
