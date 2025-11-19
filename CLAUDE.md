# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MAI Framework** is a production-ready AI application framework built on **Pydantic AI**. It provides type-safe AI agents with comprehensive memory management, tool orchestration, and enterprise-grade observability. The target deployment is a small-scale environment using LM Studio (local LLM), Qdrant (vector store), PostgreSQL with pgvector, and Redis.

## Essential Commands

### Development Server
```bash
# Start the API (correct path - NOT src.api.main:app)
poetry run uvicorn src.main:app --reload --port 8000

# Install dependencies
poetry install
```

### Testing
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test markers
poetry run pytest -m unit
poetry run pytest -m integration
poetry run pytest -m e2e

# Run a single test file
poetry run pytest tests/unit/core/agents/test_state_management.py -v

# Run a single test function
poetry run pytest tests/unit/core/agents/test_state_management.py::test_function_name -v
```

### Code Quality
```bash
# Format code
poetry run black src tests

# Lint
poetry run ruff check src tests

# Type checking
poetry run mypy src

# Pre-commit hooks
poetry run pre-commit install
poetry run pre-commit run --all-files
```

### Database
```bash
# Run migrations
poetry run alembic upgrade head

# Create new migration
poetry run alembic revision --autogenerate -m "description"
```

## Architecture Overview

### Core Component Interaction

The framework follows a **layered architecture** with strict separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI API Layer                        │
│              (src/api/routes/agents.py)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  Core Framework Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Agents     │  │    Tools     │  │   Memory     │     │
│  │  (base.py)   │  │ (registry)   │  │(short/long)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              Infrastructure Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  PostgreSQL  │  │    Redis     │  │   Qdrant     │     │
│  │ (asyncpg)    │  │  (pooling)   │  │  (vectors)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │
                    ┌────▼─────┐
                    │LM Studio │
                    │(Port 1234)│
                    └──────────┘
```

### Agent Execution Flow

Understanding this flow is critical for debugging and extending the system:

1. **API Request** → `POST /api/v1/agents/run/{agent_name}`
2. **Agent Creation** → `_create_agent_instance()`:
   - Retrieves agent class from `AgentRegistry` (singleton)
   - Creates LM Studio model with `create_lmstudio_model_async()`
   - Loads tools from `ToolRegistry` (singleton)
   - Instantiates `BaseAgentFramework` with tools
3. **Dependency Setup** → Creates `AgentDependencies`:
   - Redis client for session memory
   - Session ID for conversation continuity
   - User ID for context
4. **Agent Execution** → `agent.run_async()`:
   - Loads conversation history from Redis (`ConversationMemory`)
   - Adds user message to memory
   - Calls Pydantic AI agent with registered tools
   - Tools available for function calling
   - Adds assistant response to memory
   - Returns structured result
5. **Response** → `AgentRunResponse` with metadata

### Tool System Architecture

Tools use a **decorator pattern** with automatic registration:

```python
@tool(name="calculate", description="...", category="math")
def calculate(operation: str, a: float, b: float) -> float:
    # Implementation
```

**What happens:**
1. Decorator extracts function signature
2. Generates Pydantic models for input validation (`ParametersModel`)
3. Generates schema for return type validation
4. Creates `ToolMetadata` object
5. Wraps function with validation logic
6. Auto-registers with global `ToolRegistry`
7. Agent receives tool during initialization via `self.agent.tool()(tool_func)`

### Memory Management

**ConversationMemory (Short-term)**:
- Stored in Redis with key: `conversation_memory:{session_id}`
- Structure: JSON array of `Message` objects (role, content, timestamp, metadata)
- Methods: `add_message()`, `get_messages()`, `save_to_redis()`, `load_from_redis()`
- Token counting: Approximate (~4 chars per token)
- Lifecycle: Loaded at request start, updated during execution, saved at completion

**LongTermMemory** (PostgreSQL + Qdrant):
- Implementation exists but **not yet integrated** into agent execution flow
- Will provide semantic search via embeddings

## Critical Design Patterns

### 1. Singleton Registries (Thread-Safe)

Both `AgentRegistry` and `ToolRegistry` are **thread-safe singletons**:

```python
# Getting the singleton instance
agent_registry = AgentRegistry()  # Always returns same instance
tool_registry = ToolRegistry()    # Always returns same instance
```

**Testing Implication**: You **must** clear registries between tests to prevent cross-contamination:
```python
@pytest.fixture(autouse=True)
def clear_agent_registry():
    agent_registry.clear()
    yield
    agent_registry.clear()
```

### 2. Async-First Architecture

**Everything** uses async/await:
- Database: `AsyncSession` with asyncpg
- Redis: `async def` methods
- HTTP: `httpx.AsyncClient`
- Agent execution: `await agent.run_async()`

**Never** use synchronous blocking calls in the main execution path.

### 3. Dependency Injection via AgentDependencies

The `AgentDependencies` dataclass provides runtime dependencies to agents:

```python
@dataclass
class AgentDependencies:
    db: Optional[AsyncSession] = None
    redis: Optional[RedisClient] = None
    qdrant: Optional[QdrantVectorStore] = None
    settings: Optional[Settings] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    agent_name: Optional[str] = None
    conversation_memory: Optional[ConversationMemory] = None
```

This decouples agent logic from infrastructure, making testing easier.

### 4. Pydantic Settings Hierarchy

Configuration uses nested Pydantic Settings:

```python
Settings
├── LMStudioSettings
├── DatabaseSettings
├── RedisSettings
├── QdrantSettings
├── JWTSettings
├── MemorySettings
├── ToolSettings
├── PipelineSettings
├── RateLimitSettings
├── MetricsSettings
└── SentrySettings
```

Access via: `get_settings().lm_studio.base_url`

Environment variables use double underscore: `LM_STUDIO__BASE_URL`

## Important Testing Patterns

### Mock Strategy

The test suite heavily mocks external dependencies:

```python
# Mock Redis
@pytest.fixture
def mock_redis_client():
    mock = AsyncMock(spec=RedisClient)
    # Configure mock behavior
    return mock

# Mock Pydantic AI Agent
@pytest.fixture
def mock_pydantic_ai_agent_sync():
    mock_agent = MagicMock(spec=Agent)
    mock_result = MagicMock()
    mock_result.data = ChatResponse(role="assistant", content="Test response")
    mock_agent.run_sync.return_value.data = mock_result.data
    return mock_agent
```

### Registry Management in Tests

**Critical**: Always clear registries to prevent test pollution:

```python
# In conftest.py (autouse fixture)
@pytest.fixture(autouse=True)
def clear_agent_registry():
    """Clear agent registry before and after each test."""
    agent_registry.clear()
    yield
    agent_registry.clear()
```

### API Testing with TestClient

```python
from fastapi.testclient import TestClient

client = TestClient(app)
response = client.post(
    "/api/v1/agents/run/simple_agent",
    json={"user_input": "test", "session_id": "session-123"}
)
```

## Infrastructure Requirements

### Required Services

1. **PostgreSQL** (Port 5432):
   - Extension: `pgvector` (for embeddings)
   - Driver: `asyncpg`
   - Connection string: `postgresql+asyncpg://user:pass@localhost:5432/mai_framework`

2. **Redis** (Port 6379):
   - Used for: Conversation memory, caching, rate limiting
   - Key prefix: `MAI:` for all keys
   - Connection: `redis://localhost:6379/0`

3. **Qdrant** (Port 6333):
   - Vector database for semantic search
   - Collection: `mai_embeddings` (default)
   - Distance metric: Cosine
   - Vector size: 1536

4. **LM Studio** (Port 1234):
   - OpenAI-compatible local LLM server
   - Endpoint: `http://localhost:1234/v1`
   - No API key required
   - Must have a model loaded for agent execution

### Quick Infrastructure Setup

```bash
# Redis
docker run -d -p 6379:6379 redis:latest

# Qdrant
docker run -d -p 6333:6333 qdrant/qdrant

# PostgreSQL (ensure pgvector extension installed)
# LM Studio: Open app, load model, start server
```

## Key Files to Understand

### Entry Points
- `src/main.py` - FastAPI app, lifespan hooks, agent/tool registration

### Core Framework
- `src/core/agents/base.py` - `BaseAgentFramework[ResultT]` generic base class
- `src/core/agents/registry.py` - Singleton agent registry
- `src/core/tools/base.py` - `@tool()` decorator, validation wrapper
- `src/core/tools/registry.py` - Singleton tool registry
- `src/core/memory/short_term.py` - Redis-backed conversation memory

### API Layer
- `src/api/routes/agents.py` - 4 endpoints (run, stream, history, delete)
- `src/api/schemas/agents.py` - Pydantic request/response models

### Infrastructure
- `src/infrastructure/cache/redis_client.py` - Async Redis with pooling
- `src/infrastructure/database/session.py` - AsyncSession factory
- `src/infrastructure/database/models.py` - SQLAlchemy ORM models

### Configuration
- `src/core/utils/config.py` - Settings hierarchy with validation
- `.env.example` - Environment variable template

## Common Gotchas

### 1. Wrong Uvicorn Path

❌ **Wrong**: `poetry run uvicorn src.api.main:app --reload`
✅ **Correct**: `poetry run uvicorn src.main:app --reload`

The README.md has an error - the correct path is `src.main:app`.

### 2. Singleton Registry State

When testing, registry state persists across tests unless explicitly cleared. Always use `autouse=True` fixture to clear registries.

### 3. Async Context Required for Model Creation

`create_lmstudio_model_async()` requires an async context. Don't call it from synchronous code:

```python
# ❌ Wrong
model = create_lmstudio_model_async()  # In sync function

# ✅ Correct
model = await create_lmstudio_model_async()  # In async function
```

### 4. Tool Decorator Auto-Registration

Tools are registered **when the decorator is applied**, not when imported. Import tool modules to trigger registration:

```python
# In src/main.py
from src.core.tools import examples as tool_examples  # Triggers registration
```

### 5. Pydantic AI Tool Registration

Tools must be registered with the Pydantic AI agent using `agent.tool()()`:

```python
# In BaseAgentFramework._register_tools()
for tool_func, metadata in self.tools:
    self.agent.tool()(tool_func)  # Note the double parentheses
```

### 6. Prompt Template Security

The prompt system uses a **secure Jinja2 sandbox** that prevents attribute access on dicts. Use bracket notation:

❌ **Wrong**: `{{ user.name }}`
✅ **Correct**: `{{ user['name'] }}`

## Current Implementation Status

### ✅ Complete
- Infrastructure layer (DB, Redis, Qdrant clients)
- Agent framework with tool integration
- Tool system with decorators and validation
- Short-term memory (Redis-backed)
- API endpoints (run, stream, history, delete)
- Request/response schemas
- SSE streaming support
- Configuration management
- Logging with Loguru
- Exception hierarchy
- Example tools (8 utility/math/conversion functions)

### ⏳ In Progress / Planned
- Tool call tracking in responses (infrastructure exists, not extracting from Pydantic AI)
- Config overrides (temperature, max_tokens) application
- Long-term memory integration with Qdrant
- Semantic search functionality
- Pipeline orchestration (DAG-based, parallel execution)
- Rate limiting implementation
- Prometheus metrics collection
- Complete JWT authentication
- Integration tests for full workflows

### 📝 Known Limitations
- Authentication is currently a placeholder (`get_current_user` returns mock data)
- LongTermMemory implemented but not integrated into agent execution
- Tool call information not extracted from Pydantic AI execution results
- No metrics collection yet
- Pipeline system is empty (planned feature)

## Working with Archon (Task Management)

This project uses **Archon MCP** for task management. When working on tasks:

1. **Check current tasks**:
   ```python
   # Via Archon MCP tools
   mcp__archon__find_tasks(project_id="9a3c0349-8011-4aeb-9382-c28036d5d457")
   ```

2. **Update task status** when starting work:
   ```python
   mcp__archon__manage_task(
       action="update",
       task_id="task-id-here",
       status="doing"
   )
   ```

3. **Mark complete** when done:
   ```python
   mcp__archon__manage_task(
       action="update",
       task_id="task-id-here",
       status="review"  # or "done"
   )
   ```

**Project ID**: `9a3c0349-8011-4aeb-9382-c28036d5d457`

## Debugging Tips

### Enable Debug Logging
Set in `.env`:
```
LOG_LEVEL=DEBUG
DEBUG=true
```

### Check Agent Registration
```python
from src.core.agents.registry import agent_registry
print(agent_registry.list_agents())
```

### Check Tool Registration
```python
from src.core.tools.registry import tool_registry
tools = tool_registry.list_all_tools()
print(f"Registered tools: {len(tools)}")
for func, metadata in tools:
    print(f"  - {metadata.name} ({metadata.category})")
```

### Verify Redis Connection
```python
from src.infrastructure.cache.redis_client import get_redis_client
redis = await get_redis_client()
await redis.ping()  # Should return True
```

### Test LM Studio Connection
```python
from src.core.models.lmstudio_provider import lmstudio_health_check
health = await lmstudio_health_check()
print(health)  # Shows connection status and loaded model
```

## API Documentation

Once the server is running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/

## Additional Documentation

- `README.md` - Quick start guide and project overview
- `IMPLEMENTATION_SUMMARY.md` - Detailed implementation notes for Agent Execution Endpoints
- `HANDOFF_PROMPT.md` - Context for understanding project status and priorities
