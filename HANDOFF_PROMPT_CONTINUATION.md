# Handoff Prompt: MAI Framework Implementation Continuation

## Problem Summary

You are continuing the implementation of **MAI Framework** (Modern AI Framework), a production-ready, reusable AI application framework built on Pydantic AI. The framework provides a modular, type-safe foundation for building AI agents with comprehensive memory management, tool systems, and observability.

**Current Status**: 11 of 37 tasks completed (30% complete)
- ✅ Phase 1: Project Setup (4/4 tasks) - 100% Complete
- ✅ Phase 2: Infrastructure (4/4 tasks) - 100% Complete
- ⏳ Phase 3: Core Framework (3/7 tasks) - 43% Complete
  - ✅ Base Agent System
  - ✅ Tool System Implementation
  - ⏳ Memory System - Short-term (In Progress)
- ⏳ Phases 4-9: Not Started (26 tasks remaining)

**Your Mission**: Continue implementation from Phase 3 (Core Framework), focusing on the Memory System (Short-term and Long-term) and Prompt Management. Build on the established agent and tool systems to enable robust conversation handling and state management.

---

## Environment Details

### Working Directory
```
/Users/maxwell/Projects/ai_framework_1
```

### Repository Information
- **Git Repo**: Yes (partially managed)
- **Branch**: N/A
- **Python Version**: 3.11+ (Running 3.14 in `.venv`)
- **Package Manager**: Poetry (configured via pyproject.toml, but using `.venv` with pip for current session)

### External Services (Required for Development)
```
LM Studio Server: http://localhost:1234/v1
- GET  /v1/models              # Model detection
- POST /v1/chat/completions     # Chat completions
- POST /v1/embeddings           # Vector embeddings

PostgreSQL: postgresql+asyncpg://postgres:postgres@localhost:5432/mai_framework
Redis: redis://localhost:6379/0
Qdrant: http://localhost:6333
```

### Archon Project Management
```
Project ID: 9a3c0349-8011-4aeb-9382-c28036d5d457
Project Name: MAI Framework Implementation
Total Tasks: 37 tasks across 8 features
```

### Available Documentation Sources in Archon Knowledge Base
**IMPORTANT**: Use these source_ids when searching for implementation guidance:
```python
# Pydantic AI Documentation
source_id="473e7956a86382e6"

# FastAPI Documentation
source_id="c889b62860c33a44"

# Redis Documentation
source_id="c96cbb09b23070da"

# Qdrant Documentation (Vector Search)
# (Use general search or specific source if added)
```

---

## Verification Commands

### 1. Verify Project Structure
```bash
# Check directory structure
tree src -L 3

# Verify Core Framework components
ls -la src/core/agents/base.py
ls -la src/core/tools/base.py
ls -la src/core/tools/registry.py
ls -la src/core/tools/decorators.py
```

### 2. Check Python Environment & Tests
```bash
# Run existing tests to verify foundation
export PYTHONPATH=$PYTHONPATH:. && .venv/bin/pytest tests/temp_verify_tools.py -v
# Note: You may need to install pytest-asyncio if missing
```

### 3. Check Archon Task Status
```python
# Get current task (Memory System - Short-term)
mcp__archon__find_tasks(task_id="8e2e43b3-fee1-4d56-b102-13e23e7a803c")

# Get next priority tasks
mcp__archon__find_tasks(
    project_id="9a3c0349-8011-4aeb-9382-c28036d5d457",
    filter_by="status",
    filter_value="todo",
    per_page=5
)
```

---

## What's Been Completed in Phase 3

### 1. Base Agent System ✅
**File**: `src/core/agents/base.py`
- Implemented `BaseAgentFramework` generic class.
- Integrated `pydantic_ai.Agent`.
- Added dependency injection via `AgentDependencies`.
- Implemented `run`, `run_async`, and `run_stream` with logging and error handling.
- **Key Note**: `pydantic-ai` v1.19 uses `output_type` instead of `result_type`.

### 2. Tool System ✅
**Files**: `src/core/tools/`
- **Models**: `ToolMetadata` Pydantic model.
- **Base**: `@tool` decorator that:
  - Inspects function signatures to generate JSON schemas.
  - Creates dynamic Pydantic models for input/output validation.
  - Registers tools automatically.
  - Wraps execution with validation and logging.
- **Registry**: Thread-safe `ToolRegistry` singleton.
- **Decorators**: 
  - `@with_retry` (using `tenacity`)
  - `@with_timeout` (async support, warning for sync)
  - `@with_cache` (Redis-based)
  - `@with_rate_limit` (Redis sliding window)

---

## Next Priority Tasks (Core Framework Phase)

### 1. Memory System - Short-term (task_order: 70) ⭐ **CURRENT TASK**
**Task ID**: `8e2e43b3-fee1-4d56-b102-13e23e7a803c`
**File**: `src/core/memory/short_term.py`, `src/core/memory/models.py`

**Requirements**:
- **Models**: Define `Message` model (role, content, timestamp, metadata).
- **Class**: `ConversationMemory`.
- **Methods**:
  - `add_message(role, content)`: Add to history.
  - `get_context_string()`: Format for LLM (support different formats).
  - `count_tokens()`: Approximate counting.
  - `truncate_to_fit(max_tokens)`: Sliding window strategy.
  - `save_to_redis()`: Persist session to Redis.
  - `load_from_redis()`: Restore session.
- **Context**: Needs to work with `AgentDependencies` to be injected into agents.

**Implementation Pattern**:
```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from src.infrastructure.cache.redis_client import RedisClient

class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)

class ConversationMemory:
    def __init__(self, session_id: str, redis: RedisClient):
        self.session_id = session_id
        self.redis = redis
        self.messages: List[Message] = []
    
    # ... implementation ...
```

### 2. Memory System - Long-term (task_order: 63)
**Task ID**: `70a493a1-ba8b-4368-a049-ee4806089288`
**File**: `src/core/memory/long_term.py`

**Requirements**:
- Semantic search using Qdrant.
- Persistent storage in PostgreSQL (`Memory` model).
- Importance scoring and embedding generation via LM Studio.

### 3. Prompt Management System (task_order: 56)
**Task ID**: `2fc62572-b8cd-4787-8484-c73bc7067ec8`
**Files**: `src/core/prompts/`

**Requirements**:
- YAML-based prompt templates with Jinja2 rendering.
- Versioning and caching.

---

## Coding Standards & Tips

1.  **Async First**: All I/O (Redis, DB, AI calls) must be async.
2.  **Type Safety**: Use Pydantic models for all data structures.
3.  **Error Handling**: Use `src/core/utils/exceptions.py`.
4.  **Logging**: Use `src/core/utils/logging.py` with context.
5.  **Testing**: Write a verify script (like `tests/verify_memory.py`) for every new component. The existing `tests/temp_verify_tools.py` is a good reference for mocking Redis.

## Common Issues

-   **Pydantic V2**: Be careful with `model_validate` vs `parse_obj` (use `model_validate`). Use `RootModel` for list/scalar wrapping.
-   **Redis Mocking**: When testing decorators or memory, you likely need to mock `RedisClient`. See `tests/temp_verify_tools.py` for a working mock implementation (especially `lrange` and `ltrim`).
-   **Asyncio Warnings**: Use `inspect.iscoroutinefunction` instead of `asyncio.iscoroutinefunction` to avoid deprecation warnings.

## Success Criteria for Next Session
- [ ] `Message` model defined.
- [ ] `ConversationMemory` implemented with add/get/truncate logic.
- [ ] Redis persistence (save/load) working and tested.
- [ ] Integration test showing memory being saved and reloaded.
- [ ] Task `8e2e43b3-fee1-4d56-b102-13e23e7a803c` marked as DONE in Archon.