# Handoff Prompt: MAI Framework Implementation Continuation

## Executive Summary

You are continuing the implementation of **MAI Framework** (Modern AI Framework), a production-ready, reusable AI application framework built on Pydantic AI. The framework provides a modular, type-safe foundation for building AI agents with comprehensive memory management, tool systems, and observability.

**Current Status**: 5 of 37 tasks completed (14% complete)
- ✅ Phase 1: Project Setup (4/4 tasks complete)
- ✅ Phase 2: Infrastructure (1/5 tasks complete)
- ⏳ Phase 2: Infrastructure (4 tasks remaining)
- ⏳ Phases 3-8: Not started (28 tasks remaining)

**Your Mission**: Continue implementation from Phase 2 (Infrastructure), following the detailed task list in Archon project management system, and complete all remaining phases through production deployment.

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
- GET  /v1/models
- POST /v1/chat/completions
- POST /v1/embeddings

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

### Available Documentation Sources in Archon
**IMPORTANT**: Use these source_ids when searching for implementation guidance:
- **Pydantic AI**: `473e7956a86382e6`
- **FastAPI**: `c889b62860c33a44`
- **Docker**: `7aa56c980a99ef36`
- **Redis**: `c96cbb09b23070da`
- **Prometheus**: `49887810cd75cc76`
- **Sentry**: `9ebc2edccd4f2262`

Example search command:
```python
mcp__archon__rag_search_knowledge_base(
    query="async agent pydantic",
    source_id="473e7956a86382e6",
    match_count=5
)
```

---

## What's Been Completed

### Phase 1: Project Setup & Foundation ✅ (100% Complete)

#### 1. Project Structure ✅
**Files Created**:
```
/Users/maxwell/Projects/ai_framework_1/
├── pyproject.toml          # Poetry config with all dependencies
├── .env.example            # Environment variable templates
├── .gitignore              # Python gitignore
├── README.md               # Project overview and quick start
├── alembic.ini             # Alembic configuration
└── src/
    ├── core/
    │   ├── agents/         # Agent implementations
    │   ├── tools/          # Tool system
    │   ├── memory/         # Memory management
    │   ├── prompts/        # Prompt templates
    │   ├── pipeline/       # Pipeline orchestration
    │   ├── models/         # LM Studio provider
    │   └── utils/          # Configuration, logging, exceptions
    ├── infrastructure/
    │   ├── database/       # PostgreSQL + SQLAlchemy
    │   ├── cache/          # Redis client
    │   └── vector_store/   # Qdrant client
    ├── api/
    │   ├── routes/         # API endpoints
    │   └── middleware/     # Auth, logging middleware
    └── use_cases/          # Example implementations
```

#### 2. Configuration Management System ✅
**File**: `src/core/utils/config.py`

**Implementation Highlights**:
- Pydantic-settings based configuration with validation
- Nested settings classes for all components:
  - `LMStudioSettings` (base_url, api_key, model_name, max_tokens, temperature, timeout)
  - `DatabaseSettings` (url, pool_size, max_overflow, pool_timeout, echo)
  - `RedisSettings` (url, max_connections, timeout, decode_responses)
  - `QdrantSettings` (url, api_key, collection_name, vector_size, distance_metric)
  - `JWTSettings` (secret, algorithm, access_token_expire_minutes, refresh_token_expire_days)
  - `MemorySettings`, `ToolSettings`, `PipelineSettings`, `RateLimitSettings`, `MetricsSettings`, `SentrySettings`
- Environment variable support with `__` delimiter for nested config
- `.env` file loading with validation
- Global `get_settings()` function for singleton pattern
- `reload_settings()` for testing

**Key Configuration**:
```python
settings = get_settings()
settings.lm_studio.base_url  # http://localhost:1234/v1
settings.database.url        # postgresql+asyncpg://...
settings.jwt.secret          # Configurable JWT secret
```

#### 3. Logging & Observability Setup ✅
**Files**:
- `src/core/utils/logging.py`
- `src/api/middleware/logging.py`

**Implementation Highlights**:
- Loguru-based logging with:
  - Colored console output for development
  - JSON file output for production (`logs/app.json`)
  - Log rotation (500MB files, 10 days retention)
  - Separate error log (`logs/error.log`)
- Correlation ID support via ContextVars:
  - `get_correlation_id()`, `set_correlation_id()`, `clear_correlation_id()`
- Context binding for agent_name, user_id:
  - `get_logger_with_context(agent_name="...", user_id="...")`
- FastAPI middleware in `LoggingMiddleware`:
  - Auto-generates correlation IDs
  - Logs request/response with timing
  - Adds `X-Correlation-ID` header to responses
- Optional Sentry integration with `setup_sentry()`
- Execution logging decorator `@log_execution`

#### 4. Exception Handling System ✅
**File**: `src/core/utils/exceptions.py`

**Implementation Highlights**:
- Base `MAIException` class with:
  - `error_code`: Unique identifier
  - `message`: Human-readable message
  - `details`: Additional context (dict)
  - `retryable`: Boolean flag for retry logic
  - `to_dict()`: Serialization for API responses
- Specialized exceptions:
  - `AgentExecutionError`, `ToolExecutionError` (retryable=True)
  - `ConfigurationError`, `ValidationError` (retryable=False)
  - `AuthenticationError`, `AuthorizationError` (retryable=False)
  - `MemoryError`, `ModelError` (retryable=True)
  - `PipelineError`, `ResourceNotFoundError`
  - `TimeoutError`, `RateLimitError` (retryable=True)

**Usage Pattern**:
```python
raise AgentExecutionError(
    message="Agent failed to execute",
    agent_name="sentiment_analyzer",
    details={"input": user_input},
    retryable=True
)
```

#### 5. Database Setup with SQLAlchemy ✅
**Files**:
- `src/infrastructure/database/base.py`
- `src/infrastructure/database/session.py`
- `src/infrastructure/database/models.py`
- `src/infrastructure/database/migrations/env.py`
- `src/infrastructure/database/migrations/script.py.mako`

**Implementation Highlights**:

**base.py**:
- `Base`: DeclarativeBase for all models
- `TimestampMixin`: Auto `created_at`, `updated_at` timestamps
- `SoftDeleteMixin`: `deleted_at` field with `soft_delete()`, `restore()` methods
- `BaseModel`: Combines all mixins with UUID primary key, auto-tablename generation, `to_dict()` method

**session.py**:
- Async SQLAlchemy engine with connection pooling
- `init_db()`: Initialize global engine and session factory
- `close_db()`: Cleanup resources
- `get_db()`: FastAPI dependency for database sessions (yields session, auto-commits/rollbacks)
- `get_session()`: Context manager for manual session usage

**models.py**:
- `User`: username, email, hashed_password, is_active, is_superuser, full_name
- `UserSession`: JWT token management with access_token, refresh_token, expires_at, is_revoked
- `Conversation`: agent_name, title, is_archived, metadata
- `Message`: role (user/assistant/system/tool), content, tool_name, tool_result, metadata
- `Memory`: **pgvector support** with `embedding` field (Vector(1536)), memory_type, importance, accessed_count
- Proper indexes for performance:
  - Composite indexes on user_id + created_at
  - Vector index using ivfflat with cosine similarity
  - Foreign keys with CASCADE delete

**Alembic Configuration**:
- `alembic.ini`: Main configuration
- `env.py`: Async migration support, loads settings from config
- `script.py.mako`: Migration template
- `versions/`: Directory for migration files (empty, needs initial migration)

---

## Verification Commands

### 1. Verify Project Structure
```bash
# Check all files were created
ls -la /Users/maxwell/Projects/ai_framework_1

# Verify source directory structure
tree src -L 2
```

### 2. Verify Configuration System
```python
# Test configuration loading
cd /Users/maxwell/Projects/ai_framework_1
python3 -c "from src.core.utils.config import get_settings; s = get_settings(); print(f'LM Studio: {s.lm_studio.base_url}'); print(f'Database: {s.database.url}')"

# Expected output:
# LM Studio: http://localhost:1234/v1
# Database: postgresql+asyncpg://postgres:postgres@localhost:5432/mai_framework
```

### 3. Verify Exception System
```python
# Test exception serialization
python3 -c "from src.core.utils.exceptions import AgentExecutionError; e = AgentExecutionError('Test', agent_name='test'); print(e.to_dict())"

# Expected output:
# {'error_code': 'AGENT_EXECUTION_ERROR', 'message': 'Test', 'details': {'agent_name': 'test'}, 'retryable': True, 'exception_type': 'AgentExecutionError'}
```

### 4. Verify Database Models
```python
# Test model imports
python3 -c "from src.infrastructure.database.models import User, Memory; print('Models loaded successfully')"

# Expected output:
# Models loaded successfully
```

### 5. Check Archon Task Status
```python
# Get completed tasks
mcp__archon__find_tasks(
    project_id="9a3c0349-8011-4aeb-9382-c28036d5d457",
    filter_by="status",
    filter_value="done"
)

# Get next pending task
mcp__archon__find_tasks(
    project_id="9a3c0349-8011-4aeb-9382-c28036d5d457",
    filter_by="status",
    filter_value="todo",
    per_page=1
)
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
# Search for implementation guidance
mcp__archon__rag_search_knowledge_base(
    query="async pydantic agent",  # Keep queries SHORT (2-5 keywords)
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
The task_order field indicates priority (higher = more important). Generally:
- Infrastructure tasks (task_order 94-112)
- Core Framework tasks (task_order 49-88)
- API Layer tasks (task_order 6-41)
- Testing tasks (task_order 39-66)
- Documentation tasks (task_order 42-48)
- Deployment tasks (task_order 12-34)
- Examples & Polish (task_order 5-36)

### Phase 2: Infrastructure (Continue Here - 4 Tasks Remaining)

#### Next Task: Redis Cache Layer (task_order: 106)
**Task ID**: `169a670e-bf33-45e8-9af0-efb5e41e4ef4`
**File**: `src/infrastructure/cache/redis_client.py`

**Requirements**:
1. Search Archon for Redis async client patterns:
   ```python
   mcp__archon__rag_search_code_examples(
       query="async redis client",
       source_id="c96cbb09b23070da",
       match_count=5
   )
   ```

2. Implement async Redis client wrapper:
   - Use `redis.asyncio` library
   - Connection pooling from settings
   - Methods:
     - `get(key)`, `set(key, value, ttl)`, `delete(key)`, `exists(key)`
     - `increment(key)`, `decrement(key)` for rate limiting
     - `hget()`, `hset()`, `hgetall()` for hash operations
     - `lpush()`, `rpush()`, `lrange()` for list operations
   - JSON serialization/deserialization for complex values
   - Key prefix support: `MAI:cache:`, `MAI:session:`, `MAI:ratelimit:`
   - Health check method: `ping()`
   - Retry logic with exponential backoff

3. Example usage pattern:
   ```python
   class RedisClient:
       def __init__(self, settings: RedisSettings):
           self.settings = settings
           self.pool = None
           self.client = None

       async def connect(self):
           # Create connection pool

       async def disconnect(self):
           # Close connections

       async def set(self, key: str, value: Any, ttl: int = None):
           # Serialize value to JSON, set with TTL

       async def get(self, key: str) -> Any:
           # Get value, deserialize from JSON
   ```

#### Remaining Infrastructure Tasks (in order):

**Task 2: Qdrant Vector Store Integration** (task_order: 100)
- Task ID: `82b7a435-7ba4-416b-80f1-58fdae879043`
- File: `src/infrastructure/vector_store/qdrant_client.py`
- Search: `mcp__archon__rag_search_knowledge_base(query="qdrant vector search")`

**Task 3: JWT Authentication System** (task_order: 94)
- Task ID: `14dc54d5-d6da-4ae7-b7ea-7778764246cb`
- Files: `src/core/utils/auth.py`, `src/api/middleware/auth.py`
- Implements: token creation/verification, password hashing (bcrypt cost 12), FastAPI dependencies

**Task 4: Database Migrations** (task_order: 27)
- Task ID: `bed57b32-7df6-48aa-be48-8f899e82f1af`
- Create initial Alembic migration with pgvector extension
- Script: `scripts/migrate.py` for migration helpers

### Phase 3: Core Framework (7 Tasks)

After Infrastructure, implement core framework components:

1. **LM Studio Model Provider** (task_order: 88)
   - Task ID: `63b9b64f-4729-44fc-8141-237713b1cef3`
   - File: `src/core/models/lmstudio_provider.py`
   - Search Pydantic AI docs for OpenAI-compatible provider

2. **Base Agent System** (task_order: 82)
   - Task ID: `81cce2a0-6b64-4a57-90cd-28466152814d`
   - File: `src/core/agents/base.py`
   - Generic[ResultT] with Pydantic AI integration

3. **Tool System Implementation** (task_order: 76)
   - Task ID: `1cb5d64e-a668-4051-96e6-efd128fac9e5`
   - Files: `src/core/tools/base.py`, `registry.py`, `decorators.py`

4. **Memory System - Short-term** (task_order: 70)
   - Task ID: `8e2e43b3-fee1-4d56-b102-13e23e7a803c`
   - File: `src/core/memory/short_term.py`
   - Redis-backed conversation memory

5. **Memory System - Long-term** (task_order: 63)
   - Task ID: `70a493a1-ba8b-4368-a049-ee4806089288`
   - File: `src/core/memory/long_term.py`
   - PostgreSQL + Qdrant semantic search

6. **Prompt Management System** (task_order: 56)
   - Task ID: `2fc62572-b8cd-4787-8484-c73bc7067ec8`
   - Files: `src/core/prompts/template.py`, `registry.py`

7. **Pipeline System** (task_order: 49)
   - Task ID: `4bc94d9e-159b-4b6c-bfaf-fcd461f979e3`
   - File: `src/core/pipeline/base.py`
   - Sequential, parallel, DAG execution

### Phase 4: API Layer (5 Tasks)

1. **FastAPI Application Setup** (task_order: 41)
2. **Health Check & Metrics Endpoints** (task_order: 32)
3. **Authentication Endpoints** (task_order: 23)
4. **Agent Execution Endpoints** (task_order: 14)
5. **Memory Management Endpoints** (task_order: 6)

### Phase 5: Testing (5 Tasks)
### Phase 6: Documentation (2 Tasks)
### Phase 7: Deployment (4 Tasks)
### Phase 8: Examples (3 Tasks)
### Phase 9: Polish (3 Tasks)

---

## Implementation Workflow

### For Each Task:

```python
# STEP 1: Get next task from Archon
tasks = mcp__archon__find_tasks(
    project_id="9a3c0349-8011-4aeb-9382-c28036d5d457",
    filter_by="status",
    filter_value="todo",
    per_page=5
)
# Sort by task_order descending, pick highest

# STEP 2: Mark as doing
mcp__archon__manage_task(
    action="update",
    task_id="<task_id>",
    status="doing"
)

# STEP 3: Create TodoWrite sub-tasks
TodoWrite(todos=[
    {"content": "Search Archon docs for examples", "status": "in_progress", "activeForm": "..."},
    {"content": "Implement core functionality", "status": "pending", "activeForm": "..."},
    {"content": "Add error handling", "status": "pending", "activeForm": "..."},
    {"content": "Write tests", "status": "pending", "activeForm": "..."},
])

# STEP 4: Search Archon knowledge base
mcp__archon__rag_search_knowledge_base(
    query="<relevant keywords>",
    source_id="<appropriate docs>",
    match_count=5
)

# STEP 5: Implement with proper error handling
# - Use custom exceptions from src/core/utils/exceptions.py
# - Add logging with get_logger_with_context()
# - Follow type hints and Pydantic validation
# - Write docstrings for all functions/classes

# STEP 6: Update TodoWrite as you complete sub-tasks

# STEP 7: Mark Archon task as done
mcp__archon__manage_task(
    action="update",
    task_id="<task_id>",
    status="done"
)
```

---

## Success Criteria

### Immediate Next Steps (Infrastructure Phase)
- [ ] Redis Cache Layer implemented and tested
- [ ] Qdrant Vector Store client implemented with collection management
- [ ] JWT Authentication system with bcrypt password hashing
- [ ] Initial Alembic migration created with pgvector extension
- [ ] All Infrastructure tasks marked "done" in Archon

### Phase Completion Criteria
Each phase is complete when:
- [ ] All tasks for that phase marked "done" in Archon
- [ ] All files created with proper docstrings and type hints
- [ ] No linting errors (if linting configured)
- [ ] Key functionality manually tested (unit tests come later)

### Overall Project Success
- [ ] All 37 tasks completed in Archon
- [ ] Framework can execute a simple agent with LM Studio
- [ ] Memory persistence works (short-term, long-term, semantic)
- [ ] API endpoints return proper responses
- [ ] Tests pass (unit, integration, e2e)
- [ ] Documentation complete
- [ ] Docker deployment works

---

## Common Issues & Solutions

### Issue 1: "Module not found" errors
**Solution**:
- Ensure all `__init__.py` files exist (they do)
- Run from project root: `cd /Users/maxwell/Projects/ai_framework_1`
- Use absolute imports: `from src.core.utils.config import get_settings`

### Issue 2: Pydantic validation errors in settings
**Solution**:
- Check `.env.example` for required variables
- Create `.env` file with actual values
- Use environment variable delimiter `__` for nested settings:
  ```bash
  LM_STUDIO__BASE_URL=http://localhost:1234/v1
  DATABASE__URL=postgresql+asyncpg://...
  ```

### Issue 3: Async database connection errors
**Solution**:
- Ensure PostgreSQL is running
- Call `init_db()` before using database:
  ```python
  from src.infrastructure.database.session import init_db
  init_db()
  ```
- Use `await` for all async operations

### Issue 4: Missing pgvector extension
**Solution**:
- Install in PostgreSQL:
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  ```
- Will be automated in Alembic migration

### Issue 5: LM Studio connection refused
**Solution**:
- Verify LM Studio is running: `curl http://localhost:1234/v1/models`
- Check base_url in settings
- Ensure model is loaded in LM Studio UI

### Issue 6: Task order confusion
**Solution**:
- Always query Archon for next task:
  ```python
  tasks = mcp__archon__find_tasks(
      project_id="9a3c0349-8011-4aeb-9382-c28036d5d457",
      filter_by="status",
      filter_value="todo"
  )
  # Sort by task_order field (higher = more priority)
  ```

---

## Files Created So Far

```
/Users/maxwell/Projects/ai_framework_1/
├── pyproject.toml                                    # Poetry dependencies
├── .env.example                                      # Environment template
├── .gitignore                                        # Python gitignore
├── README.md                                         # Project documentation
├── alembic.ini                                       # Alembic config
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── agents/__init__.py                        # (empty, to implement)
│   │   ├── tools/__init__.py                         # (empty, to implement)
│   │   ├── memory/__init__.py                        # (empty, to implement)
│   │   ├── prompts/__init__.py                       # (empty, to implement)
│   │   ├── pipeline/__init__.py                      # (empty, to implement)
│   │   ├── models/__init__.py                        # (empty, to implement)
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── config.py                             # ✅ Complete
│   │       ├── logging.py                            # ✅ Complete
│   │       └── exceptions.py                         # ✅ Complete
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                               # ✅ Complete
│   │   │   ├── session.py                            # ✅ Complete
│   │   │   ├── models.py                             # ✅ Complete
│   │   │   └── migrations/
│   │   │       ├── env.py                            # ✅ Complete
│   │   │       ├── script.py.mako                    # ✅ Complete
│   │   │       └── versions/                         # (empty, needs migration)
│   │   ├── cache/__init__.py                         # ⏳ To implement
│   │   └── vector_store/__init__.py                  # ⏳ To implement
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/__init__.py                        # (empty, to implement)
│   │   └── middleware/
│   │       ├── __init__.py
│   │       └── logging.py                            # ✅ Complete
│   └── use_cases/__init__.py                         # (empty, to implement)
└── tests/__init__.py                                 # (empty, to implement)
```

---

## Key Dependencies Reference

```toml
# From pyproject.toml
pydantic-ai = "^0.0.14"          # Core AI framework
fastapi = "^0.115"               # API framework
uvicorn = "^0.31"                # ASGI server
sqlalchemy = "^2.0"              # ORM
asyncpg = "^0.29"                # Async PostgreSQL driver
alembic = "^1.13"                # Database migrations
redis = "^5.1"                   # Redis client
qdrant-client = "^1.11"          # Vector database
loguru = "^0.7"                  # Logging
httpx = "^0.27"                  # Async HTTP client
pyjwt = "^2.9"                   # JWT tokens
bcrypt = "^4.2"                  # Password hashing
prometheus-client = "^0.21"      # Metrics
python-dotenv = "^1.0"           # Environment variables
pgvector = "^0.3"                # PostgreSQL vector extension
```

---

## Testing Commands (Once Implemented)

```bash
# Install dependencies (when Poetry installed)
poetry install

# Run unit tests
poetry run pytest tests/unit -v

# Run integration tests
poetry run pytest tests/integration -v

# Run all tests with coverage
poetry run pytest --cov=src --cov-report=html

# Type checking
poetry run mypy src

# Linting
poetry run ruff check src

# Format code
poetry run black src
```

---

## Reference Implementation Guide

**Original Implementation Spec**: `/Users/maxwell/Projects/ai_framework_1/ULTRATHINK_IMPLEMENTATION_PROMPT.md`

This file contains:
- Complete technical specifications
- Detailed requirements for each component
- Code examples and patterns
- Acceptance criteria for each task

**Always reference this file when implementing new components.**

---

## Final Notes

1. **Prioritize task_order**: Higher values = higher priority. Infrastructure (100+) should be completed before Core Framework (50-90).

2. **Use Archon religiously**: Every task should be tracked. This ensures nothing is missed and provides clear progress visibility.

3. **Search before implementing**: The Archon knowledge base has comprehensive documentation for Pydantic AI, FastAPI, etc. Use it!

4. **Follow established patterns**: Look at completed files (config.py, logging.py, exceptions.py) for coding style, docstrings, and structure.

5. **Type hints everywhere**: This is a type-safe framework. All functions should have complete type annotations.

6. **Async by default**: All I/O operations (database, Redis, Qdrant, LM Studio) should be async.

7. **Test as you go**: While formal tests come later, manually verify each component works before moving on.

8. **Document in code**: Comprehensive docstrings for all classes and functions. Include usage examples.

---

## Ready to Continue?

**Your first task**: Implement Redis Cache Layer (task_order: 106)

Start with:
```python
# 1. Search Archon for Redis patterns
mcp__archon__rag_search_code_examples(
    query="async redis client",
    source_id="c96cbb09b23070da",
    match_count=5
)

# 2. Mark task as doing
mcp__archon__manage_task(
    action="update",
    task_id="169a670e-bf33-45e8-9af0-efb5e41e4ef4",
    status="doing"
)

# 3. Create TodoWrite tracking
# 4. Implement src/infrastructure/cache/redis_client.py
# 5. Mark complete
```

**Good luck! Build something amazing. 🚀**
