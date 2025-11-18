# Handoff Prompt: MAI Framework Implementation Continuation

## Problem Summary

You are continuing the implementation of **MAI Framework** (Modern AI Framework), a production-ready, reusable AI application framework built on Pydantic AI. The framework provides a modular, type-safe foundation for building AI agents with comprehensive memory management, tool systems, and observability.

**Current Status**: 9 of 37 tasks completed (24% complete)
- ✅ Phase 1: Project Setup (4/4 tasks) - 100% Complete
- ✅ Phase 2: Infrastructure (4/4 tasks) - 100% Complete
- ⏳ Phase 3: Core Framework (1/7 tasks) - 14% Complete
- ⏳ Phases 4-9: Not Started (27 tasks remaining)

**Your Mission**: Continue implementation from Phase 3 (Core Framework), following the detailed task list in Archon project management system. Build on the solid foundation that has been established to complete the agent system, memory layers, tools, and API endpoints.

---

## Environment Details

### Working Directory
```
/Users/maxwell/Projects/ai_framework_1
```

### Repository Information
- **Git Repo**: No (not initialized yet)
- **Branch**: N/A
- **Python Version**: 3.11+
- **Package Manager**: Poetry (configured via pyproject.toml)

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

# Docker Documentation
source_id="7aa56c980a99ef36"

# Redis Documentation
source_id="c96cbb09b23070da"

# Prometheus Documentation
source_id="49887810cd75cc76"

# Sentry Documentation
source_id="9ebc2edccd4f2262"
```

**Example Search Commands**:
```python
# Search for Pydantic AI agent patterns
mcp__archon__rag_search_knowledge_base(
    query="agent system prompt tools",
    source_id="473e7956a86382e6",
    match_count=5
)

# Search for code examples
mcp__archon__rag_search_code_examples(
    query="FastAPI dependency injection",
    source_id="c889b62860c33a44",
    match_count=3
)
```

---

## Verification Commands

### 1. Verify Project Structure
```bash
# Check directory structure
tree src -L 3

# Verify all infrastructure files exist
ls -la src/infrastructure/cache/redis_client.py
ls -la src/infrastructure/vector_store/qdrant_client.py
ls -la src/infrastructure/database/models.py
ls -la src/core/utils/auth.py
ls -la src/core/models/lmstudio_provider.py
```

### 2. Check Python Environment
```python
# Test configuration loading
cd /Users/maxwell/Projects/ai_framework_1
python3 -c "from src.core.utils.config import get_settings; s = get_settings(); print(f'LM Studio: {s.lm_studio.base_url}'); print(f'Database: {s.database.url}')"

# Expected output:
# LM Studio: http://localhost:1234/v1
# Database: postgresql+asyncpg://postgres:postgres@localhost:5432/mai_framework
```

### 3. Test Infrastructure Components
```python
# Test Redis client (requires Redis running)
python3 -c "
import asyncio
from src.infrastructure.cache.redis_client import RedisClient

async def test():
    client = RedisClient()
    await client.connect()
    health = await client.health_check()
    print(f'Redis: {health}')
    await client.disconnect()

asyncio.run(test())
"

# Test Qdrant client (requires Qdrant running)
python3 -c "
import asyncio
from src.infrastructure.vector_store.qdrant_client import QdrantVectorStore

async def test():
    client = QdrantVectorStore()
    await client.connect()
    health = await client.health_check()
    print(f'Qdrant: {health}')
    await client.disconnect()

asyncio.run(test())
"

# Test LM Studio connection (requires LM Studio running)
python3 -c "
import asyncio
from src.core.models.lmstudio_provider import lmstudio_health_check

async def test():
    health = await lmstudio_health_check()
    print(f'LM Studio: {health}')

asyncio.run(test())
"
```

### 4. Check Archon Task Status
```python
# Get current tasks in progress
mcp__archon__find_tasks(
    project_id="9a3c0349-8011-4aeb-9382-c28036d5d457",
    filter_by="status",
    filter_value="doing"
)

# Get next todo task by priority
mcp__archon__find_tasks(
    project_id="9a3c0349-8011-4aeb-9382-c28036d5d457",
    filter_by="status",
    filter_value="todo",
    per_page=5
)
# Sort by task_order descending to get highest priority
```

---

## What's Been Completed

### Phase 1: Project Setup ✅ (100% Complete)

#### Files Created:
```
/Users/maxwell/Projects/ai_framework_1/
├── pyproject.toml              # Poetry config with all dependencies
├── .env.example                # Environment variable templates
├── .gitignore                  # Python gitignore
├── README.md                   # Basic project overview
├── alembic.ini                 # Alembic configuration
└── src/
    ├── core/utils/
    │   ├── config.py           # ✅ Pydantic Settings configuration
    │   ├── logging.py          # ✅ Loguru setup with correlation IDs
    │   └── exceptions.py       # ✅ Custom exception hierarchy
    ├── infrastructure/database/
    │   ├── base.py             # ✅ SQLAlchemy base models
    │   ├── session.py          # ✅ Async session management
    │   ├── models.py           # ✅ User, Memory, Conversation models
    │   └── migrations/
    │       ├── env.py          # ✅ Alembic async support
    │       └── script.py.mako  # ✅ Migration template
    └── api/middleware/
        └── logging.py          # ✅ FastAPI logging middleware
```

#### Key Features Implemented:
1. **Configuration System** (`src/core/utils/config.py`):
   - Pydantic-settings based with validation
   - Nested settings for all components (LMStudio, Database, Redis, Qdrant, JWT, etc.)
   - Environment variable support with `__` delimiter
   - Global `get_settings()` singleton

2. **Logging System** (`src/core/utils/logging.py`):
   - Loguru-based with colored console + JSON file output
   - Log rotation (500MB files, 10 days retention)
   - Correlation ID support via ContextVars
   - Context binding for agent_name, user_id
   - Optional Sentry integration

3. **Exception Handling** (`src/core/utils/exceptions.py`):
   - Base `MAIException` with error_code, message, details, retryable flag
   - 13 specialized exceptions (AgentExecutionError, ToolExecutionError, etc.)
   - Serialization for API responses

4. **Database Models** (`src/infrastructure/database/models.py`):
   - `User`: username, email, hashed_password, is_active, is_superuser
   - `UserSession`: JWT token management
   - `Conversation`: agent conversations with metadata
   - `Message`: role-based messages (user/assistant/system/tool)
   - `Memory`: **pgvector support** with embedding field (Vector(1536))
   - Proper indexes including vector ivfflat with cosine similarity

### Phase 2: Infrastructure ✅ (100% Complete)

#### 1. Redis Cache Layer (`src/infrastructure/cache/redis_client.py`)
**685 lines** - Production-ready async Redis wrapper

**Key Features**:
- Async operations using `redis.asyncio`
- Connection pooling (configurable via settings)
- Basic operations: `get()`, `set()`, `delete()`, `exists()`
- Counter operations: `increment()`, `decrement()` (for rate limiting)
- Hash operations: `hget()`, `hset()`, `hgetall()`, `hdel()`
- List operations: `lpush()`, `rpush()`, `lrange()`, `llen()`
- JSON serialization/deserialization for complex Python objects
- Key prefix support: `MAI:cache:`, `MAI:session:`, `MAI:ratelimit:`
- Retry logic with exponential backoff (configurable max_retries)
- Health check: `ping()`, `health_check()`
- Context manager support (`async with`)

**Usage Example**:
```python
from src.infrastructure.cache.redis_client import RedisClient

async with RedisClient() as redis:
    await redis.set("user:123", {"name": "John", "age": 30}, ttl=3600)
    user = await redis.get("user:123")
    # user = {"name": "John", "age": 30}
```

#### 2. Qdrant Vector Store (`src/infrastructure/vector_store/qdrant_client.py`)
**684 lines** - Async Qdrant client for semantic search

**Key Features**:
- Collection management: `create_collection()`, `delete_collection()`, `collection_exists()`, `get_collection_info()`
- Vector operations: `upsert()`, `batch_upsert()`, `search()`, `delete()`
- Configurable distance metrics (Cosine, Dot Product, Euclidean)
- Metadata filtering for precise searches
- Default collection: "mai_embeddings" (1536-dimensional vectors)
- Batch upsert with configurable batch size
- Health checks with collection status
- Context manager support

**Usage Example**:
```python
from src.infrastructure.vector_store.qdrant_client import QdrantVectorStore

async with QdrantVectorStore() as qdrant:
    # Create collection
    await qdrant.create_collection("memories", vector_size=1536)

    # Upsert vectors
    await qdrant.upsert(
        collection_name="memories",
        vectors=[embedding1, embedding2],
        payloads=[{"text": "hello", "user_id": "123"}, {"text": "world", "user_id": "123"}],
        ids=["id1", "id2"]
    )

    # Semantic search with filtering
    results = await qdrant.search(
        collection_name="memories",
        query_vector=query_embedding,
        limit=5,
        filter_metadata={"user_id": "123"}
    )
```

#### 3. JWT Authentication System

**File: `src/core/utils/auth.py`** (461 lines)

**Key Features**:
- JWT token creation: `create_access_token()`, `create_refresh_token()`
- JWT verification: `verify_token()` with expiration handling
- Password hashing with **bcrypt cost factor 12**: `hash_password()`, `verify_password()`
- `TokenPayload` class for structured payload management
- Utility functions: `get_token_expiration()`, `is_token_expired()`
- Comprehensive error handling with AuthenticationError exceptions

**File: `src/api/middleware/auth.py`** (340 lines)

**Key Features**:
- FastAPI authentication middleware and dependencies
- Token extraction from `Authorization: Bearer <token>` headers
- User retrieval dependencies:
  - `get_current_user()` - Fetches user from database, validates active status
  - `get_current_active_user()` - Ensures user is active
  - `get_current_superuser()` - Ensures superuser privileges
  - `get_optional_user()` - Optional authentication for public endpoints
- Type-annotated shortcuts: `CurrentUser`, `CurrentActiveUser`, `CurrentSuperuser`, `OptionalUser`
- Proper error responses with WWW-Authenticate headers

**Usage Example**:
```python
from fastapi import APIRouter, Depends
from src.api.middleware.auth import CurrentUser, CurrentSuperuser
from src.infrastructure.database.models import User

router = APIRouter()

@router.get("/me")
async def get_me(current_user: CurrentUser):
    return {"id": str(current_user.id), "username": current_user.username}

@router.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, current_user: CurrentSuperuser):
    # Only superusers can access this endpoint
    return {"status": "deleted"}
```

#### 4. Database Infrastructure (`src/infrastructure/database/`)

**Files**:
- `base.py` - Base models with UUID, timestamps, soft delete
- `session.py` - Async engine, session factory, `get_db()` dependency
- `models.py` - User, UserSession, Conversation, Message, Memory models
- `migrations/env.py` - Alembic async support
- `migrations/script.py.mako` - Migration template

**Key Features**:
- Async SQLAlchemy with asyncpg driver
- Connection pooling (configurable pool size)
- `get_db()` FastAPI dependency with auto-commit/rollback
- pgvector support for Memory model embeddings
- Proper indexes for performance
- Soft delete support on all models
- Timestamp mixins for created_at/updated_at

### Phase 3: Core Framework (Partial - 1/7 Complete)

#### LM Studio Model Provider (`src/core/models/lmstudio_provider.py`)
**335 lines** - OpenAI-compatible Pydantic AI integration

**Key Features**:
- Factory functions: `create_lmstudio_model()`, `create_lmstudio_model_async()`
- Auto-detection: `detect_lmstudio_model()` - queries `/v1/models` endpoint
- Connection testing: `test_lmstudio_connection()`, `lmstudio_health_check()`
- Uses Pydantic AI's `OpenAIChatModel` with custom `OpenAIProvider`
- Supports all OpenAI-compatible features (chat, streaming, embeddings)
- Configurable timeout and retry settings

**Usage Example**:
```python
from pydantic_ai import Agent
from src.core.models.lmstudio_provider import get_lmstudio_model_async

# Auto-detect model from LM Studio
model = await get_lmstudio_model_async()

# Create agent
agent = Agent(model=model, system_prompt="You are a helpful assistant.")

# Run agent
result = await agent.run("What is 2+2?")
print(result.data)  # "4"
```

---

## Task: Continue MAI Framework Implementation

### Critical Instructions

**1. ALWAYS Use Archon for Task Management**
```python
# Before starting ANY task:
# 1. Find the highest priority task
tasks = mcp__archon__find_tasks(
    project_id="9a3c0349-8011-4aeb-9382-c28036d5d457",
    filter_by="status",
    filter_value="todo"
)
# Sort by task_order descending (higher = more priority)

# 2. Mark task as "doing"
mcp__archon__manage_task(
    action="update",
    task_id="<task_id>",
    status="doing"
)

# 3. Implement the task
# ... your implementation ...

# 4. Mark task as "done"
mcp__archon__manage_task(
    action="update",
    task_id="<task_id>",
    status="done"
)
```

**2. ALWAYS Use TodoWrite for Sub-task Tracking**
- Break each Archon task into 3-6 sub-tasks
- Track progress with TodoWrite tool
- Mark sub-tasks completed immediately after finishing

**3. ALWAYS Search Archon Knowledge Base Before Implementing**
```python
# Search for implementation guidance (keep queries SHORT - 2-5 keywords)
mcp__archon__rag_search_knowledge_base(
    query="agent system prompt",  # SHORT query
    source_id="473e7956a86382e6",  # Pydantic AI docs
    match_count=5
)

# Search for code examples
mcp__archon__rag_search_code_examples(
    query="FastAPI middleware",
    source_id="c889b62860c33a44",  # FastAPI docs
    match_count=3
)
```

**4. Follow Implementation Order by task_order**

The task_order field indicates priority (higher = more important). Tasks are already sorted by priority in Archon.

---

## Next Priority Tasks (Core Framework Phase)

### 1. Base Agent System (task_order: 82) ⭐ **NEXT TASK**
**Task ID**: `81cce2a0-6b64-4a57-90cd-28466152814d`
**File**: `src/core/agents/base.py`

**Requirements**:
- Implement `BaseAgentFramework` class with `Generic[ResultT]` (NOT unused `T`)
- Integration with Pydantic AI `Agent` class
- System prompt support
- Tool registration and management
- Dependency injection for context (database, Redis, Qdrant, config)
- Result validation using Pydantic models
- Streaming support
- Retry logic with exponential backoff
- Error handling with custom exceptions
- Methods to implement:
  - `validate_dependencies()` - Check required dependencies are available
  - `get_conversation_context()` - Build context from memory
  - `log_execution()` - Log agent execution with metrics
  - `run()` - Execute agent synchronously
  - `run_async()` - Execute agent asynchronously
  - `run_stream()` - Execute with streaming support

**Implementation Pattern**:
```python
from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel
from pydantic_ai import Agent
from src.core.utils.logging import get_logger_with_context

ResultT = TypeVar('ResultT', bound=BaseModel)

class BaseAgentFramework(Generic[ResultT]):
    \"\"\"Base class for AI agents in MAI Framework.

    Provides common functionality for all agents including:
    - System prompt management
    - Tool registration
    - Dependency injection
    - Result validation
    - Logging and metrics
    \"\"\"

    def __init__(
        self,
        name: str,
        model: Any,
        system_prompt: str,
        result_type: type[ResultT],
        **dependencies
    ):
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        self.result_type = result_type
        self.dependencies = dependencies
        self.logger = get_logger_with_context(agent_name=name)

        # Create Pydantic AI agent
        self.agent = Agent(
            model=self.model,
            result_type=self.result_type,
            system_prompt=self.system_prompt
        )

    async def run_async(self, user_input: str, **kwargs) -> ResultT:
        # Validate dependencies
        # Get conversation context
        # Execute agent
        # Log execution
        # Return validated result
        pass
```

**Search Archon for Examples**:
```python
mcp__archon__rag_search_knowledge_base(
    query="agent generic result type",
    source_id="473e7956a86382e6",
    match_count=5
)

mcp__archon__rag_search_code_examples(
    query="pydantic ai agent tools",
    source_id="473e7956a86382e6",
    match_count=5
)
```

### 2. Tool System Implementation (task_order: 76)
**Task ID**: `1cb5d64e-a668-4051-96e6-efd128fac9e5`
**Files**: `src/core/tools/base.py`, `registry.py`, `decorators.py`

**Requirements**:
- Tool decorator for automatic registration
- Thread-safe global tool registry
- Tool metadata (name, description, parameters, categories)
- Tool versioning support
- Decorators: `@with_retry`, `@with_timeout`, `@with_cache` (via Redis), `@with_rate_limit`
- Input/output validation using Pydantic
- Execution logging with metrics
- Category-based filtering
- Enable/disable tools dynamically

**Implementation Pattern**:
```python
# base.py
from typing import Callable, Any
from pydantic import BaseModel

class ToolMetadata(BaseModel):
    name: str
    description: str
    category: str
    version: str = "1.0.0"
    enabled: bool = True

def tool(
    name: str,
    description: str,
    category: str = "general"
) -> Callable:
    \"\"\"Decorator for registering a tool.\"\"\"
    def decorator(func: Callable) -> Callable:
        # Register tool in global registry
        # Wrap with logging and validation
        return func
    return decorator

# registry.py
class ToolRegistry:
    \"\"\"Thread-safe global tool registry.\"\"\"
    _instance = None
    _tools: dict[str, Callable] = {}

    def register(self, name: str, func: Callable, metadata: ToolMetadata):
        # Thread-safe registration
        pass

    def get(self, name: str) -> Optional[Callable]:
        # Get tool by name
        pass

    def list_by_category(self, category: str) -> list[Callable]:
        # Filter by category
        pass

# decorators.py
def with_cache(ttl: int = 300):
    \"\"\"Cache tool results in Redis.\"\"\"
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Check cache
            # Execute if not cached
            # Store in cache
            pass
        return wrapper
    return decorator
```

### 3. Memory System - Short-term (task_order: 70)
**Task ID**: `8e2e43b3-fee1-4d56-b102-13e23e7a803c`
**File**: `src/core/memory/short_term.py`

**Requirements**:
- `ConversationMemory` class for managing conversation history
- `Message` Pydantic model (role, content, timestamp)
- Methods:
  - `add_message()` - Add message to history
  - `get_messages()` - Get all messages
  - `get_context_string()` - Format messages as string (simple/chat/xml formats)
  - `count_tokens()` - Approximate token count
  - `truncate_to_fit()` - Trim to max tokens/messages
  - `save_to_redis()` - Persist to Redis
  - `load_from_redis()` - Load from Redis
- Max 10 messages or 4000 tokens (configurable)
- Automatic summarization for old context

**Implementation Pattern**:
```python
from pydantic import BaseModel
from datetime import datetime
from src.infrastructure.cache.redis_client import RedisClient

class Message(BaseModel):
    role: str  # user, assistant, system, tool
    content: str
    timestamp: datetime
    metadata: dict = {}

class ConversationMemory:
    def __init__(
        self,
        session_id: str,
        max_messages: int = 10,
        max_tokens: int = 4000
    ):
        self.session_id = session_id
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.messages: list[Message] = []

    async def save_to_redis(self, redis: RedisClient):
        key = f"MAI:session:{self.session_id}"
        data = [m.model_dump() for m in self.messages]
        await redis.set(key, data, ttl=3600)

    async def load_from_redis(self, redis: RedisClient):
        key = f"MAI:session:{self.session_id}"
        data = await redis.get(key)
        if data:
            self.messages = [Message(**m) for m in data]
```

### 4. Memory System - Long-term (task_order: 63)
**Task ID**: `70a493a1-ba8b-4368-a049-ee4806089288`
**File**: `src/core/memory/long_term.py`

**Requirements**:
- `LongTermMemory` class for persistent semantic memory
- Integration with PostgreSQL (Memory model) and Qdrant (vectors)
- Methods:
  - `store()` - Store memory in DB + vector store
  - `retrieve()` - Semantic search for relevant memories
  - `get_recent()` - Get recent memories by timestamp
  - `update_access()` - Track memory access count
  - `calculate_importance()` - LLM-based importance scoring
  - `cleanup_old_memories()` - Delete low-importance old memories
  - `_generate_embedding()` - Generate vector via LM Studio `/v1/embeddings`
- Access tracking (accessed_count, last_accessed_at)
- Importance scoring (0.0 to 1.0)

**Implementation Pattern**:
```python
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database.models import Memory
from src.infrastructure.vector_store.qdrant_client import QdrantVectorStore
import httpx

class LongTermMemory:
    def __init__(
        self,
        db: AsyncSession,
        vector_store: QdrantVectorStore,
        user_id: str
    ):
        self.db = db
        self.vector_store = vector_store
        self.user_id = user_id

    async def _generate_embedding(self, text: str) -> list[float]:
        \"\"\"Generate embedding via LM Studio.\"\"\"
        settings = get_settings()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.lm_studio.base_url}/embeddings",
                json={"input": text, "model": "local-model"}
            )
            data = response.json()
            return data["data"][0]["embedding"]

    async def store(self, content: str, metadata: dict = None) -> str:
        # Generate embedding
        embedding = await self._generate_embedding(content)

        # Store in database
        memory = Memory(
            user_id=self.user_id,
            content=content,
            embedding=embedding,
            metadata=metadata or {}
        )
        self.db.add(memory)
        await self.db.commit()

        # Store in vector store
        await self.vector_store.upsert(
            collection_name="mai_memories",
            vectors=[embedding],
            payloads=[{"content": content, "user_id": self.user_id, **metadata}],
            ids=[str(memory.id)]
        )

        return str(memory.id)
```

### 5. Prompt Management System (task_order: 56)
**Task ID**: `2fc62572-b8cd-4787-8484-c73bc7067ec8`
**Files**: `src/core/prompts/template.py`, `registry.py`

**Requirements**:
- `PromptTemplate` Pydantic model
- `PromptManager` for loading/rendering YAML-based prompts
- Jinja2 sandboxed template support
- Version management for prompts
- Variable validation
- Prompt caching in Redis
- Security: prevent template injection
- Create example prompts in `config/prompts/base/system.yaml`

### 6. Pipeline System (task_order: 49)
**Task ID**: `4bc94d9e-159b-4b6c-bfaf-fcd461f979e3`
**File**: `src/core/pipeline/base.py`

**Requirements**:
- `PipelineStage` abstract base class
- `Pipeline` with `Generic[InputT, OutputT]`
- Sequential execution
- Parallel execution
- DAG-based execution with dependencies
- Error strategies: fail_fast, continue, retry
- Stage dependencies
- Intermediate result caching
- Metrics collection (duration, success rate per stage)
- Retry failed stages
- Visualization helper: `to_dict()`, `to_json()`

---

## Implementation Workflow for Each Task

### Step-by-Step Process:

**Step 1: Get Next Task from Archon**
```python
tasks = mcp__archon__find_tasks(
    project_id="9a3c0349-8011-4aeb-9382-c28036d5d457",
    filter_by="status",
    filter_value="todo",
    per_page=10
)
# Manually sort by task_order descending, pick highest
```

**Step 2: Mark Task as Doing**
```python
mcp__archon__manage_task(
    action="update",
    task_id="<task_id>",
    status="doing"
)
```

**Step 3: Create TodoWrite Sub-tasks**
```python
TodoWrite(todos=[
    {"content": "Search Archon for examples", "status": "in_progress", "activeForm": "Searching Archon"},
    {"content": "Implement core class/function", "status": "pending", "activeForm": "Implementing core"},
    {"content": "Add error handling", "status": "pending", "activeForm": "Adding error handling"},
    {"content": "Add logging and metrics", "status": "pending", "activeForm": "Adding logging"},
    {"content": "Update __init__.py exports", "status": "pending", "activeForm": "Updating exports"},
])
```

**Step 4: Search Archon Knowledge Base**
```python
# Search for patterns (keep queries SHORT)
mcp__archon__rag_search_knowledge_base(
    query="<2-5 keywords>",
    source_id="<appropriate docs>",
    match_count=5
)
```

**Step 5: Implement with Best Practices**
- Use custom exceptions from `src/core/utils/exceptions.py`
- Add logging with `get_logger_with_context()`
- Follow type hints and Pydantic validation
- Write comprehensive docstrings with usage examples
- Add context manager support (`async with`) where appropriate
- Include health check methods for infrastructure components

**Step 6: Update TodoWrite as You Complete Sub-tasks**

**Step 7: Mark Archon Task as Done**
```python
mcp__archon__manage_task(
    action="update",
    task_id="<task_id>",
    status="done"
)
```

---

## Coding Standards & Best Practices

### 1. Type Hints Everywhere
```python
# Good
async def get_user(user_id: UUID) -> User:
    ...

# Bad
async def get_user(user_id):
    ...
```

### 2. Async by Default
All I/O operations must be async:
- Database operations
- Redis operations
- Qdrant operations
- LM Studio API calls
- HTTP requests

### 3. Error Handling
Use custom exceptions with proper error codes:
```python
from src.core.utils.exceptions import ModelError, MemoryError

try:
    result = await model.run(input)
except Exception as e:
    raise ModelError(
        f"Model execution failed: {e}",
        model_name=model.name,
        details={"input": input, "error": str(e)}
    )
```

### 4. Logging with Context
```python
from src.core.utils.logging import get_logger_with_context

logger = get_logger_with_context(agent_name="my_agent", user_id="123")
logger.info("Processing request", request_id="req_123")
```

### 5. Configuration
Always use settings, never hardcode:
```python
from src.core.utils.config import get_settings

settings = get_settings()
base_url = settings.lm_studio.base_url  # NOT http://localhost:1234
```

### 6. Pydantic Models for Data Validation
```python
from pydantic import BaseModel, Field

class AgentRequest(BaseModel):
    user_input: str = Field(..., min_length=1, max_length=5000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=8192)
```

### 7. Docstrings
Include usage examples in all docstrings:
```python
def create_agent(name: str, model: Any) -> Agent:
    \"\"\"Create a new agent instance.

    Args:
        name: Unique agent name
        model: Pydantic AI model instance

    Returns:
        Configured agent instance

    Example:
        ```python
        from src.core.models import get_lmstudio_model

        model = get_lmstudio_model()
        agent = create_agent("my_agent", model)
        result = await agent.run("Hello!")
        ```
    \"\"\"
```

---

## Common Issues & Solutions

### Issue 1: "Module not found" errors
**Solution**:
- All `__init__.py` files should export public APIs
- Run from project root: `cd /Users/maxwell/Projects/ai_framework_1`
- Use absolute imports: `from src.core.utils.config import get_settings`

### Issue 2: Pydantic validation errors
**Solution**:
- Check `.env.example` for required variables
- Create `.env` file with actual values
- Use `__` delimiter for nested settings:
  ```bash
  LM_STUDIO__BASE_URL=http://localhost:1234/v1
  DATABASE__URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mai_framework
  ```

### Issue 3: Async database connection errors
**Solution**:
- Ensure PostgreSQL is running
- Call `init_db()` before using database:
  ```python
  from src.infrastructure.database.session import init_db
  await init_db()
  ```
- Always use `await` for async operations

### Issue 4: Redis connection refused
**Solution**:
- Verify Redis is running: `redis-cli ping` (should return "PONG")
- Check Redis URL in settings: `redis://localhost:6379/0`
- Ensure no firewall blocking port 6379

### Issue 5: Qdrant connection refused
**Solution**:
- Verify Qdrant is running: `curl http://localhost:6333/collections`
- Check Qdrant URL in settings: `http://localhost:6333`
- Ensure no firewall blocking port 6333

### Issue 6: LM Studio connection refused
**Solution**:
- Verify LM Studio is running: `curl http://localhost:1234/v1/models`
- Ensure a model is loaded in LM Studio UI
- Check base_url in settings matches LM Studio port

### Issue 7: pgvector extension missing
**Solution**:
- Install in PostgreSQL:
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  ```
- Will be automated in Alembic migration task

---

## Files to Review for Context

### Configuration & Setup:
- `src/core/utils/config.py` - All settings and environment variables
- `src/core/utils/exceptions.py` - Custom exception hierarchy
- `src/core/utils/logging.py` - Logging setup

### Infrastructure (All Complete):
- `src/infrastructure/cache/redis_client.py` - Redis operations
- `src/infrastructure/vector_store/qdrant_client.py` - Vector operations
- `src/infrastructure/database/models.py` - Database schema
- `src/infrastructure/database/session.py` - Database session management
- `src/core/utils/auth.py` - JWT and password utilities
- `src/api/middleware/auth.py` - FastAPI auth dependencies

### Core Framework (Partial):
- `src/core/models/lmstudio_provider.py` - LM Studio integration

### Dependencies:
- `pyproject.toml` - Lines 10-50 (all Python dependencies)
- `.env.example` - Environment variable template

---

## Success Criteria

### Per-Task Success:
- [ ] All code follows type hints and Pydantic validation
- [ ] Comprehensive docstrings with usage examples
- [ ] Proper error handling with custom exceptions
- [ ] Logging with context binding
- [ ] Unit tests (if in testing phase)
- [ ] Task marked "done" in Archon
- [ ] TodoWrite sub-tasks all completed

### Phase Completion (Core Framework):
- [ ] All 7 Core Framework tasks completed in Archon
- [ ] Base agent can execute with LM Studio
- [ ] Tools can be registered and executed
- [ ] Short-term memory persists in Redis
- [ ] Long-term memory persists in PostgreSQL + Qdrant
- [ ] Prompts load from YAML and render with Jinja2
- [ ] Pipelines can execute sequential/parallel stages

### Overall Project Success (End Goal):
- [ ] All 37 tasks completed in Archon (100%)
- [ ] Framework can execute a multi-turn conversation
- [ ] Memory persistence works across sessions
- [ ] API endpoints return proper responses
- [ ] Tests pass (unit, integration, e2e)
- [ ] Documentation complete
- [ ] Docker deployment works

---

## Next Steps for Fresh Agent

**Immediate Action**:
1. Query Archon for next highest priority task:
   ```python
   mcp__archon__find_tasks(
       project_id="9a3c0349-8011-4aeb-9382-c28036d5d457",
       filter_by="status",
       filter_value="todo",
       per_page=5
   )
   ```
2. Sort by `task_order` descending
3. Start with **Base Agent System** (task_order: 82)
4. Follow the implementation workflow above

**Remember**:
- Search Archon knowledge base BEFORE implementing
- Use TodoWrite to track sub-tasks
- Mark tasks in Archon as "doing" → "done"
- Follow coding standards and best practices
- Write comprehensive docstrings and tests

---

## Reference Files

**Original Spec**: `/Users/maxwell/Projects/ai_framework_1/ULTRATHINK_IMPLEMENTATION_PROMPT.md`

This file contains:
- Complete technical specifications
- Detailed requirements for each component
- Code examples and patterns
- Acceptance criteria

**Previous Handoff**: `/Users/maxwell/Projects/ai_framework_1/HANDOFF_PROMPT.md`

Contains earlier context and completed work summary.

---

## Final Notes

**You have a solid foundation**:
- ✅ All infrastructure is complete (Redis, Qdrant, Database, Auth)
- ✅ LM Studio integration is ready
- ✅ Configuration, logging, and exceptions are production-ready

**What's next**:
- 🔧 Build the core framework (agents, tools, memory, prompts, pipelines)
- 🌐 Create API endpoints for agent execution
- 🧪 Write comprehensive tests
- 📚 Document everything
- 🚀 Deploy with Docker

**The framework is 24% complete. Keep the momentum going! 🚀**
