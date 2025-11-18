# MAI Framework Implementation Guide

## Executive Summary

You are tasked with implementing **MAI**, a production-ready, reusable AI application framework built on Pydantic AI. This framework provides a modular, type-safe foundation for building AI agents with comprehensive memory management, tool systems, and observability.

**Target Specifications:**
- **Scale**: Small deployment (single server, <1000 users)
- **LLM Provider**: LM Studio (local, OpenAI-compatible) at `http://localhost:1234`
- **Vector Database**: Qdrant (dedicated vector DB)
- **Authentication**: JWT tokens (stateless)
- **Memory**: Full stack (short-term, long-term, semantic)
- **Architecture**: General-purpose framework shell (not use-case specific)

## Critical Context

### User's Environment
```
LM Studio Server Endpoints:
- GET  http://localhost:1234/v1/models
- POST http://localhost:1234/v1/responses
- POST http://localhost:1234/v1/chat/completions
- POST http://localhost:1234/v1/completions
- POST http://localhost:1234/v1/embeddings
```

### Available Documentation in Archon Knowledge Base
- **Pydantic AI Documentation** (source_id: `473e7956a86382e6`)
- **FastAPI Documentation** (source_id: `c889b62860c33a44`)
- **Docker Documentation** (source_id: `7aa56c980a99ef36`)
- **Redis Documentation** (source_id: `c96cbb09b23070da`)
- **Prometheus Documentation** (source_id: `49887810cd75cc76`)
- **Sentry Documentation** (source_id: `9ebc2edccd4f2262`)

**Use these sources when implementing components!**

---

## PHASE 1: Project Setup & Foundation

### Task 1.1: Initialize Project Structure
**Description**: Create the complete directory structure and initialize Python project with dependencies.

**Requirements**:
- Create all directories as specified in project structure
- Initialize Python project with `pyproject.toml` (use Poetry or Rye)
- Pin Python version to 3.11+
- Create `.env.example` with all required environment variables
- Create `.gitignore` for Python projects
- Add `README.md` with quick start instructions

**Key Dependencies** (minimum versions):
```toml
python = "^3.11"
pydantic = "^2.9"
pydantic-ai = "^0.0.14"
fastapi = "^0.115"
uvicorn = {extras = ["standard"], version = "^0.30"}
sqlalchemy = {extras = ["asyncio"], version = "^2.0"}
asyncpg = "^0.29"
alembic = "^1.13"
redis = {extras = ["hiredis"], version = "^5.0"}
qdrant-client = "^1.11"
loguru = "^0.7"
python-jose = {extras = ["cryptography"], version = "^3.3"}
passlib = {extras = ["bcrypt"], version = "^1.7"}
httpx = "^0.27"
pytest = "^8.3"
pytest-asyncio = "^0.24"
python-multipart = "^0.0.9"
pyyaml = "^6.0"
jinja2 = "^3.1"
opentelemetry-api = "^1.25"
opentelemetry-sdk = "^1.25"
prometheus-client = "^0.20"
sentry-sdk = {extras = ["fastapi"], version = "^2.0"}
```

**Acceptance Criteria**:
- [ ] All directories created
- [ ] `pyproject.toml` with all dependencies
- [ ] `.env.example` with commented examples
- [ ] Project installs without errors
- [ ] README with setup instructions

---

### Task 1.2: Configuration Management System
**Description**: Implement the configuration system with environment-based overrides and secrets management.

**File**: `src/core/utils/config.py`

**Requirements**:
- Use `pydantic-settings` for configuration
- Support `.env` file loading
- Support YAML configuration files with environment overrides
- Implement configuration validation
- Add configuration for:
  - LM Studio endpoint (`http://localhost:1234`)
  - Database (PostgreSQL)
  - Redis
  - Qdrant
  - JWT settings (secret, algorithm, expiration)
  - Logging level
  - API settings

**Example Structure**:
```python
class LMStudioSettings(BaseModel):
    base_url: str = "http://localhost:1234"
    api_key: Optional[str] = None  # LM Studio doesn't require key
    timeout: int = 300
    max_retries: int = 3

class DatabaseSettings(BaseModel):
    url: str
    pool_size: int = 5
    max_overflow: int = 10
    echo: bool = False

class Settings(BaseSettings):
    # App
    app_name: str = "MAI"
    app_version: str = "1.0.0"
    debug: bool = False

    # LM Studio
    lm_studio: LMStudioSettings = Field(default_factory=LMStudioSettings)

    # Database
    database: DatabaseSettings

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None

    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440  # 24 hours

    # Logging
    log_level: str = "INFO"
    log_file: Optional[Path] = None

    # Sentry
    sentry_dsn: Optional[str] = None

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"
```

**Acceptance Criteria**:
- [ ] Settings class with all required fields
- [ ] Environment variable loading works
- [ ] Configuration validation raises clear errors
- [ ] LM Studio settings properly configured
- [ ] Configuration can be accessed globally via singleton

---

### Task 1.3: Logging & Observability Setup
**Description**: Configure structured logging with Loguru and basic observability infrastructure.

**File**: `src/core/utils/logging.py`

**Requirements**:
- Configure Loguru with:
  - Console output (colored, human-readable)
  - File output (JSON format for parsing)
  - Log rotation (500MB per file, 10 days retention)
  - Different log levels per output
- Add correlation ID support for request tracing
- Integrate with FastAPI middleware
- Add optional Sentry integration
- Create logger binding helpers for context (agent name, user_id, etc.)

**Acceptance Criteria**:
- [ ] Loguru configured with console and file outputs
- [ ] JSON structured logging to files
- [ ] Correlation ID in all logs
- [ ] Sentry integration (conditional on DSN presence)
- [ ] Easy context binding: `logger.bind(agent="sentiment", user="123")`

---

### Task 1.4: Exception Handling System
**Description**: Create custom exception hierarchy and error handling utilities.

**File**: `src/core/utils/exceptions.py`

**Requirements**:
- Base exception class: `MAIException`
- Specific exceptions:
  - `AgentExecutionError` - Agent runtime failures
  - `ToolExecutionError` - Tool execution failures
  - `ConfigurationError` - Configuration/setup issues
  - `AuthenticationError` - Auth failures
  - `AuthorizationError` - Permission issues
  - `ValidationError` - Input validation failures
  - `MemoryError` - Memory system failures
  - `ModelError` - LLM provider errors
- Each exception should include:
  - Error code (for API responses)
  - User-friendly message
  - Technical details (for logging)
  - Optional retry flag

**Example**:
```python
class MAIException(Exception):
    """Base exception for MAI framework"""
    def __init__(
        self,
        message: str,
        code: str = "FRAMEWORK_ERROR",
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = False
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.retryable = retryable
```

**Acceptance Criteria**:
- [ ] Complete exception hierarchy
- [ ] All exceptions have error codes
- [ ] Exception serialization for API responses
- [ ] Helper function to convert exceptions to HTTP responses

---

## PHASE 2: Infrastructure Layer

### Task 2.1: Database Setup with SQLAlchemy
**Description**: Implement PostgreSQL database layer with async SQLAlchemy and pgvector support.

**Files**:
- `src/infrastructure/database/session.py`
- `src/infrastructure/database/models.py`
- `src/infrastructure/database/base.py`

**Requirements**:

1. **Session Management** (`session.py`):
   - Async engine creation
   - Session factory with connection pooling
   - Dependency injection for FastAPI
   - Transaction management utilities

2. **Base Models** (`base.py`):
   - Base class with common fields (id, created_at, updated_at)
   - UUID primary keys
   - Timestamping mixin
   - Soft delete support

3. **Domain Models** (`models.py`):
   - `User` - User accounts
   - `Session` - User sessions (for JWT tracking)
   - `Conversation` - Conversation threads
   - `Message` - Individual messages (short-term memory)
   - `Memory` - Long-term memory records
   - `Agent` - Agent configurations (optional, for multi-agent)

**Key Model: Memory Table**:
```python
class Memory(Base):
    __tablename__ = "memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))  # pgvector, dimension depends on embedding model
    metadata = Column(JSONB, default={})
    importance = Column(Float, default=0.5)
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

4. **Alembic Setup**:
   - Initialize Alembic
   - Create initial migration with all tables
   - Add pgvector extension: `CREATE EXTENSION IF NOT EXISTS vector;`

**Acceptance Criteria**:
- [ ] Async SQLAlchemy engine and session factory
- [ ] All domain models defined with relationships
- [ ] pgvector extension enabled
- [ ] Alembic configured with initial migration
- [ ] FastAPI dependency for database sessions
- [ ] Migration creates all tables successfully

---

### Task 2.2: Redis Cache Layer
**Description**: Implement Redis client for caching, session storage, and rate limiting.

**File**: `src/infrastructure/cache/redis_client.py`

**Requirements**:
- Async Redis client wrapper
- Connection pooling
- Utility methods:
  - `get(key)` / `set(key, value, ttl)`
  - `delete(key)` / `exists(key)`
  - `increment(key)` / `decrement(key)` - for rate limiting
  - `get_hash(key, field)` / `set_hash(key, field, value)`
  - `add_to_list(key, value)` / `get_list(key, start, end)`
- Serialization/deserialization (JSON)
- Key prefix support (e.g., `MAI:cache:`, `MAI:session:`)
- Health check method

**Example Usage**:
```python
cache = RedisClient()

# Cache agent response
await cache.set(
    f"response:{query_hash}",
    {"response": "...", "timestamp": ...},
    ttl=3600
)

# Rate limiting
count = await cache.increment(f"ratelimit:{user_id}:{minute}")
if count > 60:
    raise RateLimitExceeded()
```

**Acceptance Criteria**:
- [ ] Async Redis client with connection pooling
- [ ] All utility methods implemented
- [ ] Automatic JSON serialization
- [ ] Key prefix support
- [ ] Connection retry logic
- [ ] Health check method

---

### Task 2.3: Qdrant Vector Store Integration
**Description**: Implement Qdrant client for semantic memory storage and retrieval.

**File**: `src/infrastructure/vector_store/qdrant_client.py`

**Requirements**:
- Async Qdrant client wrapper
- Collection management:
  - Create collection with proper configuration
  - Delete collection
  - Get collection info
- Vector operations:
  - `upsert(collection, id, vector, payload)` - Add/update vectors
  - `search(collection, query_vector, limit, filter)` - Semantic search
  - `delete(collection, id)` - Remove vector
  - `batch_upsert(collection, records)` - Bulk operations
- Default collection for memory: `MAI_memories`
- Support for metadata filtering
- Distance metric: Cosine similarity

**Schema for Memory Collection**:
```python
{
    "vectors": {
        "size": 1536,  # Adjust based on embedding model
        "distance": "Cosine"
    },
    "payload_schema": {
        "user_id": "keyword",
        "session_id": "keyword",
        "content": "text",
        "importance": "float",
        "timestamp": "datetime",
        "metadata": "json"
    }
}
```

**Acceptance Criteria**:
- [ ] Async Qdrant client wrapper
- [ ] Collection creation and management
- [ ] Vector upsert and search operations
- [ ] Metadata filtering support
- [ ] Batch operations for performance
- [ ] Health check method
- [ ] Default collection for memories created on startup

---

### Task 2.4: JWT Authentication System
**Description**: Implement JWT token generation, validation, and middleware for FastAPI.

**Files**:
- `src/api/middleware/auth.py`
- `src/core/utils/auth.py`

**Requirements**:

1. **Token Management** (`auth.py`):
   - `create_access_token(user_id, claims)` - Generate JWT
   - `verify_token(token)` - Validate and decode JWT
   - `hash_password(password)` - Bcrypt password hashing
   - `verify_password(plain, hashed)` - Password verification
   - Token expiration handling
   - Refresh token support (optional)

2. **Authentication Middleware** (`middleware/auth.py`):
   - Extract token from `Authorization: Bearer <token>` header
   - Validate token
   - Inject user info into request state
   - Handle expired/invalid tokens gracefully
   - Public endpoints bypass (health check, docs)

3. **Dependency Injection**:
   - `get_current_user()` - FastAPI dependency for protected routes
   - `get_optional_user()` - For routes where auth is optional

**Example**:
```python
from src.core.utils.auth import create_access_token, verify_token

# Generate token
token = create_access_token(
    user_id="user-123",
    claims={"email": "user@example.com", "role": "user"}
)

# Verify token
payload = verify_token(token)
# -> {"user_id": "user-123", "email": "...", "exp": ..., "iat": ...}

# Protected route
@router.get("/me")
async def get_me(user = Depends(get_current_user)):
    return {"user_id": user["user_id"]}
```

**Acceptance Criteria**:
- [ ] JWT token creation and verification
- [ ] Password hashing with bcrypt
- [ ] Authentication middleware for FastAPI
- [ ] `get_current_user()` dependency
- [ ] Public endpoints bypass auth
- [ ] Clear error messages for auth failures
- [ ] Token expiration handled correctly

---

## PHASE 3: Core Framework Components

### Task 3.1: LM Studio Model Provider
**Description**: Create Pydantic AI model provider for LM Studio (OpenAI-compatible).

**File**: `src/core/models/lmstudio_provider.py`

**Requirements**:
- Pydantic AI uses OpenAI-compatible providers natively
- Create configuration helper for LM Studio:
  - Base URL: `http://localhost:1234/v1`
  - No API key required (or dummy key)
  - Timeout and retry configuration
- Test connection on initialization
- Support for:
  - Chat completions
  - Embeddings (for memory)
  - Streaming responses
- Model selection (list available models from `/v1/models`)

**Example**:
```python
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

def create_lmstudio_model(
    base_url: str = "http://localhost:1234/v1",
    model_name: Optional[str] = None,
    timeout: int = 300,
) -> OpenAIModel:
    """
    Create OpenAI-compatible model for LM Studio.

    If model_name is None, fetches the first available model.
    """
    if model_name is None:
        # Fetch available models
        model_name = get_first_available_model(base_url)

    return OpenAIModel(
        model_name=model_name,
        base_url=base_url,
        api_key="dummy",  # LM Studio doesn't require auth
        timeout=timeout,
    )

async def get_available_models(base_url: str) -> List[str]:
    """Fetch available models from LM Studio"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/models")
        data = response.json()
        return [model["id"] for model in data.get("data", [])]
```

**Acceptance Criteria**:
- [ ] LM Studio model provider factory
- [ ] Automatic model detection from `/v1/models`
- [ ] Connection health check
- [ ] Timeout and retry configuration
- [ ] Streaming support
- [ ] Embedding support (separate endpoint)
- [ ] Clear error messages for connection failures

---

### Task 3.2: Base Agent System
**Description**: Implement the core agent framework with proper generics and type safety.

**File**: `src/core/agents/base.py`

**Requirements**:
- Fix generic type usage (remove unused `T`, keep `ResultT`)
- Implement `BaseAgentFramework` as per specification
- Support for:
  - System prompts (static and dynamic)
  - Tool registration
  - Dependency injection
  - Result type validation
  - Streaming responses
  - Retry logic
  - Error handling
- Integration with Pydantic AI Agent
- Proper logging with agent context

**Key Fixes from Original**:
```python
# BEFORE (incorrect):
class BaseAgentFramework(ABC, Generic[T, ResultT]):
    # T is never used!

# AFTER (correct):
class BaseAgentFramework(ABC, Generic[ResultT]):
    """
    Base class for all framework agents.
    ResultT: The Pydantic model type for agent responses
    """
```

**Additional Methods**:
- `validate_dependencies(deps)` - Validate dependencies before run
- `get_conversation_context(deps)` - Build context from memory
- `log_execution(prompt, result, duration)` - Structured logging

**Acceptance Criteria**:
- [ ] BaseAgentFramework with correct generics
- [ ] All abstract methods defined
- [ ] Integration with Pydantic AI Agent
- [ ] Streaming support
- [ ] Comprehensive error handling
- [ ] Execution logging with metrics
- [ ] Documentation with examples

---

### Task 3.3: Tool System
**Description**: Implement the tool registry and decorator system.

**Files**:
- `src/core/tools/base.py`
- `src/core/tools/registry.py`
- `src/core/tools/decorators.py`

**Requirements**:

1. **Tool Registry** (`registry.py`):
   - Global tool registry (thread-safe)
   - Tool metadata storage
   - Category-based organization
   - Tool versioning
   - Enable/disable tools dynamically

2. **Tool Decorator** (`base.py`):
   - `@tool(name, description, category)` decorator
   - Automatic registration
   - Input/output validation
   - Execution logging

3. **Tool Decorators** (`decorators.py`):
   - `@with_retry(max_attempts, delay)` - Retry on failure
   - `@with_timeout(seconds)` - Timeout enforcement
   - `@with_cache(ttl)` - Result caching (using Redis)
   - `@with_rate_limit(calls_per_minute)` - Rate limiting

**Example Tool**:
```python
from src.core.tools.base import tool
from src.core.tools.decorators import with_retry, with_cache

@tool(
    name="web_search",
    description="Search the web for information",
    category="search"
)
@with_retry(max_attempts=3, delay=1.0)
@with_cache(ttl=3600)
async def web_search(
    ctx: RunContext[AgentDependencies],
    query: str,
    max_results: int = 10
) -> List[Dict[str, str]]:
    """
    Search the web and return results.

    Args:
        query: Search query
        max_results: Maximum number of results

    Returns:
        List of search results with title, url, snippet
    """
    # Implementation
    pass
```

**Acceptance Criteria**:
- [ ] Thread-safe tool registry
- [ ] Tool decorator with automatic registration
- [ ] Tool metadata tracking
- [ ] Category-based filtering
- [ ] Retry decorator with exponential backoff
- [ ] Timeout decorator
- [ ] Cache decorator (Redis-backed)
- [ ] Rate limit decorator
- [ ] Comprehensive tests for all decorators

---

### Task 3.4: Memory System - Short-term
**Description**: Implement conversation memory for maintaining context within sessions.

**File**: `src/core/memory/short_term.py`

**Requirements**:
- Implement `Message` Pydantic model
- Implement `ConversationMemory` class as specified
- Additional features:
  - Token counting (approximate)
  - Automatic truncation when token limit exceeded
  - Message summarization for old context
  - Export to various formats (list, string, chat format)
- Integration with Redis for persistence across requests

**Methods**:
```python
class ConversationMemory:
    def __init__(self, max_messages: int = 10, max_tokens: Optional[int] = 4000):
        ...

    def add_message(self, role: str, content: str, metadata: dict = None):
        """Add message to memory"""

    def get_messages(self, last_n: int = None) -> List[Message]:
        """Get recent messages"""

    def get_context_string(self, format: str = "simple") -> str:
        """Format: simple, chat, xml"""

    def count_tokens(self) -> int:
        """Approximate token count"""

    def truncate_to_fit(self, max_tokens: int):
        """Remove oldest messages to fit token limit"""

    async def save_to_redis(self, session_id: str):
        """Persist to Redis"""

    @classmethod
    async def load_from_redis(cls, session_id: str) -> "ConversationMemory":
        """Load from Redis"""
```

**Acceptance Criteria**:
- [ ] Message model with validation
- [ ] ConversationMemory with all methods
- [ ] Token counting (approximate)
- [ ] Automatic truncation
- [ ] Redis persistence
- [ ] Multiple export formats
- [ ] Unit tests

---

### Task 3.5: Memory System - Long-term
**Description**: Complete the long-term memory implementation with database and vector storage.

**File**: `src/core/memory/long_term.py`

**Requirements**:
- Complete all `pass` statements with real implementations
- Integrate with PostgreSQL (via SQLAlchemy)
- Integrate with Qdrant for semantic search
- Embedding generation (via LM Studio embeddings endpoint)
- Memory importance scoring
- Access tracking (update access_count and last_accessed)
- Memory cleanup (delete old, low-importance memories)

**Complete Methods**:
```python
class LongTermMemory:
    def __init__(
        self,
        db_session: AsyncSession,
        vector_store: QdrantClient,
        embedding_model: str = "text-embedding-ada-002"  # Or LM Studio model
    ):
        ...

    async def store(
        self,
        user_id: str,
        content: str,
        metadata: dict = None,
        importance: float = 0.5,
        session_id: str = None
    ) -> MemoryRecord:
        """Store memory in DB and vector store"""

    async def retrieve(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
        min_importance: float = 0.0
    ) -> List[MemoryRecord]:
        """Semantic search for relevant memories"""

    async def get_recent(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[MemoryRecord]:
        """Get chronologically recent memories"""

    async def update_access(self, memory_id: str):
        """Update access tracking"""

    async def calculate_importance(self, content: str) -> float:
        """Use LLM to score importance (0-1)"""

    async def cleanup_old_memories(
        self,
        user_id: str,
        keep_recent: int = 100,
        min_importance: float = 0.7
    ):
        """Remove old, unimportant memories"""

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding via LM Studio"""
        # POST to http://localhost:1234/v1/embeddings
```

**Acceptance Criteria**:
- [ ] All methods fully implemented (no `pass`)
- [ ] Database operations (CRUD)
- [ ] Qdrant vector operations
- [ ] Embedding generation via LM Studio
- [ ] Importance scoring (LLM-based)
- [ ] Access tracking
- [ ] Memory cleanup utility
- [ ] Comprehensive error handling
- [ ] Integration tests with real DB and Qdrant

---

### Task 3.6: Prompt Management System
**Description**: Implement prompt templates with versioning and variable injection.

**Files**:
- `src/core/prompts/template.py`
- `src/core/prompts/registry.py` (optional)

**Requirements**:
- `PromptTemplate` Pydantic model
- `PromptManager` class for loading/rendering
- Jinja2 template support
- YAML-based prompt definitions
- Version management (latest vs specific versions)
- Variable validation
- Prompt caching
- Security: Prevent template injection attacks

**Example Prompt File** (`config/prompts/base/system.yaml`):
```yaml
name: system_base
description: Base system prompt for all agents

latest:
  version: "2.0.0"
  template: |
    You are {{ agent_name }}, an AI assistant powered by MAI framework.

    Your capabilities:
    {% for capability in capabilities %}
    - {{ capability }}
    {% endfor %}

    {% if memory_context %}
    ## Memory Context
    {{ memory_context }}
    {% endif %}

    Current date: {{ current_date }}

    Guidelines:
    - Be helpful, accurate, and concise
    - Use tools when appropriate
    - Ask clarifying questions when needed

  variables:
    - agent_name
    - capabilities
    - current_date
    - memory_context  # optional

  metadata:
    author: "MAI Core Team"
    category: "system"

versions:
  "1.0.0":
    template: |
      You are {{ agent_name }}. Help the user.
    variables:
      - agent_name
```

**Security Considerations**:
- Sanitize user input before template rendering
- Use `jinja2.sandbox.SandboxedEnvironment` for untrusted templates
- Never allow user-provided templates without review

**Acceptance Criteria**:
- [ ] PromptTemplate model with validation
- [ ] PromptManager with YAML loading
- [ ] Jinja2 rendering with sandboxing
- [ ] Version management
- [ ] Variable validation
- [ ] Template caching
- [ ] Example prompt files for common cases
- [ ] Security tests (injection attempts)

---

### Task 3.7: Pipeline System
**Description**: Implement the pipeline orchestrator for chaining processing stages.

**File**: `src/core/pipeline/base.py`

**Requirements**:
- `PipelineStage` abstract base class
- `Pipeline` orchestrator
- Features:
  - Sequential execution (stages run in order)
  - Parallel execution (independent stages)
  - Error handling (fail-fast vs continue)
  - Stage dependencies (DAG support)
  - Intermediate result caching
  - Pipeline metrics (stage duration, success rate)
  - Retry failed stages

**Enhanced Pipeline**:
```python
class Pipeline(Generic[InputT, OutputT]):
    def __init__(self, name: str, error_strategy: str = "fail_fast"):
        """
        Args:
            error_strategy: "fail_fast" | "continue" | "retry"
        """
        self.name = name
        self.error_strategy = error_strategy
        self.stages: List[PipelineStage] = []
        self._results: Dict[str, Any] = {}
        self._metrics: Dict[str, Dict] = {}

    def add_stage(
        self,
        stage: PipelineStage,
        depends_on: List[str] = None
    ) -> "Pipeline":
        """Add stage with optional dependencies"""

    async def run(self, input_data: InputT) -> OutputT:
        """Execute pipeline with configured strategy"""

    async def _run_sequential(self, input_data):
        """Sequential execution"""

    async def _run_parallel(self, input_data):
        """Parallel execution (for independent stages)"""

    async def _run_dag(self, input_data):
        """DAG-based execution (respects dependencies)"""

    def get_metrics(self) -> Dict[str, Dict]:
        """Get execution metrics for all stages"""
```

**Acceptance Criteria**:
- [ ] PipelineStage base class
- [ ] Pipeline orchestrator
- [ ] Sequential execution
- [ ] Parallel execution
- [ ] DAG-based execution (dependencies)
- [ ] Error strategies (fail-fast, continue, retry)
- [ ] Stage metrics collection
- [ ] Intermediate result access
- [ ] Pipeline visualization helper (to_dict/to_json)

---

## PHASE 4: API Layer

### Task 4.1: FastAPI Application Setup
**Description**: Create the main FastAPI application with middleware and configuration.

**File**: `src/api/main.py`

**Requirements**:
- FastAPI app initialization
- CORS middleware (configurable origins)
- Compression middleware
- Request logging middleware
- Authentication middleware
- Rate limiting middleware (using Redis)
- Exception handlers for custom exceptions
- Startup/shutdown events:
  - Initialize database connection
  - Initialize Redis connection
  - Initialize Qdrant client
  - Test LM Studio connection
  - Create default collections in Qdrant
- API documentation (OpenAPI/Swagger)
- Health check endpoint

**Example Structure**:
```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting MAI API...")

    # Initialize connections
    await init_database()
    await init_redis()
    await init_qdrant()
    await test_lmstudio_connection()

    logger.info("API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down MAI API...")
    await close_database()
    await close_redis()
    logger.info("API shutdown complete")

app = FastAPI(
    title="MAI API",
    version="1.0.0",
    description="AI Application Framework",
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Exception handlers
@app.exception_handler(MAIException)
async def MAI_exception_handler(request: Request, exc: MAIException):
    return JSONResponse(
        status_code=500 if not exc.retryable else 503,
        content={
            "error": exc.message,
            "code": exc.code,
            "retryable": exc.retryable,
            "details": exc.details
        }
    )
```

**Acceptance Criteria**:
- [ ] FastAPI app with all middleware
- [ ] Startup/shutdown lifecycle
- [ ] CORS configuration
- [ ] Compression middleware
- [ ] Exception handlers
- [ ] OpenAPI documentation
- [ ] Health check endpoint
- [ ] Request logging

---

### Task 4.2: Health Check & Metrics Endpoints
**Description**: Implement health check and metrics endpoints for monitoring.

**File**: `src/api/routes/health.py`

**Requirements**:

1. **Health Check** (`GET /health`):
   - Overall status (healthy/degraded/unhealthy)
   - Component checks:
     - Database (can connect? latency?)
     - Redis (can connect? latency?)
     - Qdrant (can connect? latency?)
     - LM Studio (can connect? available models?)
   - Return appropriate HTTP status codes:
     - 200: All healthy
     - 503: Any component unhealthy

2. **Readiness Check** (`GET /ready`):
   - Quick check for K8s/load balancer
   - Returns 200 if app can handle requests

3. **Metrics Endpoint** (`GET /metrics`):
   - Prometheus-compatible metrics
   - Metrics to expose:
     - Request count by endpoint
     - Request duration histogram
     - Active requests gauge
     - Agent execution count and duration
     - Tool execution count and duration
     - Memory operations count
     - Error count by type
     - LM Studio API latency

**Example Response** (`/health`):
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-11-18T12:00:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "latency_ms": 2.3
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 0.8
    },
    "qdrant": {
      "status": "healthy",
      "latency_ms": 5.1,
      "collections": ["MAI_memories"]
    },
    "lm_studio": {
      "status": "healthy",
      "latency_ms": 12.4,
      "available_models": ["qwen2.5-14b-instruct"]
    }
  }
}
```

**Acceptance Criteria**:
- [ ] `/health` endpoint with component checks
- [ ] `/ready` endpoint for quick checks
- [ ] `/metrics` endpoint (Prometheus format)
- [ ] Appropriate HTTP status codes
- [ ] Component latency measurement
- [ ] Comprehensive metrics collection

---

### Task 4.3: Authentication Endpoints
**Description**: Implement user registration, login, and token management.

**File**: `src/api/routes/auth.py`

**Requirements**:

Endpoints:
1. `POST /auth/register` - Create new user account
2. `POST /auth/login` - Login and receive JWT token
3. `POST /auth/refresh` - Refresh access token (optional)
4. `POST /auth/logout` - Invalidate token
5. `GET /auth/me` - Get current user info (protected)

**Request/Response Schemas**:
```python
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: Optional[str] = None

class RegisterResponse(BaseModel):
    user_id: str
    email: str
    access_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserInfo

class UserInfo(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str]
    created_at: datetime
```

**Security Requirements**:
- Password hashing with bcrypt (cost factor 12)
- Email validation
- Rate limiting on login endpoint (5 attempts per minute per IP)
- Token blacklisting on logout (store in Redis)

**Acceptance Criteria**:
- [ ] All endpoints implemented
- [ ] Request/response validation
- [ ] Password hashing
- [ ] JWT token generation
- [ ] Rate limiting on auth endpoints
- [ ] Token blacklisting
- [ ] Input sanitization
- [ ] Clear error messages

---

### Task 4.4: Agent Execution Endpoints
**Description**: Create API endpoints for running agents and streaming responses.

**File**: `src/api/routes/agents.py`

**Requirements**:

Endpoints:
1. `POST /agents/run` - Execute agent with prompt
2. `POST /agents/stream` - Execute agent with streaming response
3. `GET /agents/history/{session_id}` - Get conversation history
4. `DELETE /agents/history/{session_id}` - Clear conversation history

**Request/Response Schemas**:
```python
class AgentRunRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=10000)
    session_id: Optional[str] = None  # For conversation continuity
    agent_config: Optional[AgentConfigOverrides] = None
    use_memory: bool = True
    memory_config: Optional[MemoryConfig] = None

class AgentConfigOverrides(BaseModel):
    temperature: Optional[float] = Field(ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(ge=1, le=4000)
    system_prompt_override: Optional[str] = None

class MemoryConfig(BaseModel):
    use_short_term: bool = True
    use_long_term: bool = True
    use_semantic: bool = True
    max_context_messages: int = 10

class AgentRunResponse(BaseModel):
    response: str
    session_id: str
    metadata: Dict[str, Any]
    tool_calls: List[ToolCall] = []
    memory_stats: MemoryStats

class ToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    result: Any
    duration_ms: float

class MemoryStats(BaseModel):
    short_term_messages: int
    long_term_retrieved: int
    semantic_results: int
```

**Implementation Details**:
- User authentication required
- Session management (create if not provided)
- Memory integration:
  - Load short-term memory from Redis
  - Retrieve relevant long-term memories
  - Perform semantic search if enabled
  - Save new messages to memory
- Tool execution tracking
- Metrics collection
- Error handling

**Streaming Response** (`/agents/stream`):
```python
@router.post("/stream")
async def stream_agent_response(
    request: AgentRunRequest,
    user = Depends(get_current_user)
) -> StreamingResponse:
    async def generate():
        async for chunk in agent.run_stream(request.prompt, deps):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"

        yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
```

**Acceptance Criteria**:
- [ ] All endpoints implemented
- [ ] Authentication required
- [ ] Session management
- [ ] Memory integration (all three types)
- [ ] Streaming support (SSE)
- [ ] Tool call tracking
- [ ] Request/response validation
- [ ] Error handling and logging
- [ ] Rate limiting per user

---

### Task 4.5: Memory Management Endpoints
**Description**: API endpoints for managing user memories.

**File**: `src/api/routes/memory.py`

**Requirements**:

Endpoints:
1. `POST /memory/store` - Manually store a memory
2. `GET /memory/search` - Semantic search in memories
3. `GET /memory/recent` - Get recent memories
4. `GET /memory/{memory_id}` - Get specific memory
5. `DELETE /memory/{memory_id}` - Delete memory
6. `POST /memory/cleanup` - Trigger memory cleanup

**Example**:
```python
class StoreMemoryRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    importance: float = Field(ge=0.0, le=1.0, default=0.5)
    metadata: Dict[str, Any] = {}

class SearchMemoryRequest(BaseModel):
    query: str
    limit: int = Field(ge=1, le=50, default=5)
    min_importance: float = Field(ge=0.0, le=1.0, default=0.0)

class MemoryResponse(BaseModel):
    id: str
    content: str
    importance: float
    created_at: datetime
    access_count: int
    metadata: Dict[str, Any]
```

**Acceptance Criteria**:
- [ ] All endpoints implemented
- [ ] Authentication required
- [ ] User isolation (users only see their memories)
- [ ] Semantic search integration
- [ ] Pagination for list endpoints
- [ ] Input validation
- [ ] Memory cleanup scheduling

---

## PHASE 5: Testing & Documentation

### Task 5.1: Unit Tests - Core Components
**Description**: Write comprehensive unit tests for core framework components.

**Files**:
- `tests/unit/core/test_agents.py`
- `tests/unit/core/test_tools.py`
- `tests/unit/core/test_memory.py`
- `tests/unit/core/test_pipeline.py`
- `tests/unit/core/test_prompts.py`

**Requirements**:
- Use pytest with pytest-asyncio
- Test coverage >80%
- Mock external dependencies (LM Studio, databases)
- Use Pydantic AI's test utilities
- Test both success and failure cases
- Parametrized tests for edge cases

**Example Test**:
```python
import pytest
from pydantic_ai.models.test import TestModel
from src.core.agents.base import BaseAgentFramework

@pytest.mark.asyncio
async def test_agent_execution_success():
    """Test successful agent execution"""
    agent = MyTestAgent()

    # Use test model
    with models.override_default_model('test'):
        result = await agent.run("Test prompt")

    assert isinstance(result, ExpectedResultType)
    assert result.field == "expected_value"

@pytest.mark.asyncio
async def test_agent_execution_with_tool():
    """Test agent execution with tool calls"""
    tool_called = False

    @tool(name="test_tool", description="Test")
    async def test_tool_fn(ctx, arg: str) -> str:
        nonlocal tool_called
        tool_called = True
        return f"Result: {arg}"

    # Test implementation
    ...

    assert tool_called
```

**Coverage Areas**:
- Agent initialization and configuration
- Tool registration and execution
- Memory storage and retrieval
- Pipeline execution (sequential, parallel, DAG)
- Prompt rendering with various inputs
- Error handling and retries
- Configuration validation

**Acceptance Criteria**:
- [ ] >80% code coverage for core components
- [ ] All core components have unit tests
- [ ] Tests use mocks for external services
- [ ] Both success and failure cases covered
- [ ] Parametrized tests for edge cases
- [ ] Tests run in <30 seconds

---

### Task 5.2: Integration Tests - API & Infrastructure
**Description**: Write integration tests for API endpoints and infrastructure components.

**Files**:
- `tests/integration/test_api.py`
- `tests/integration/test_database.py`
- `tests/integration/test_redis.py`
- `tests/integration/test_qdrant.py`
- `tests/integration/test_lmstudio.py`

**Requirements**:
- Use Docker Compose for test infrastructure
- Test real database operations
- Test real vector store operations
- Test real LM Studio integration (if available)
- Use test database (separate from dev)
- Clean up test data after each test

**Test Infrastructure** (`docker-compose.test.yml`):
```yaml
version: '3.8'
services:
  postgres-test:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: MAI_test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    ports:
      - "5433:5432"

  redis-test:
    image: redis:7-alpine
    ports:
      - "6380:6379"

  qdrant-test:
    image: qdrant/qdrant:latest
    ports:
      - "6334:6333"
```

**Example Integration Test**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_with_real_memory(test_db, test_qdrant):
    """Test agent execution with real memory storage"""
    # Setup
    user_id = "test-user"
    agent = MyAgent()
    memory = LongTermMemory(test_db, test_qdrant)

    # Store some memories
    await memory.store(user_id, "The user likes Python", importance=0.8)
    await memory.store(user_id, "The user works on AI projects", importance=0.9)

    # Run agent
    result = await agent.run(
        "What do you remember about me?",
        deps=AgentDependencies(user_id=user_id)
    )

    # Verify
    assert "Python" in result.response or "AI" in result.response

    # Cleanup
    await memory.cleanup_old_memories(user_id, keep_recent=0)
```

**Acceptance Criteria**:
- [ ] Integration tests for all API endpoints
- [ ] Database integration tests
- [ ] Redis integration tests
- [ ] Qdrant integration tests
- [ ] LM Studio integration tests (if available)
- [ ] Test infrastructure via Docker Compose
- [ ] Proper test data cleanup
- [ ] Tests can run in CI/CD

---

### Task 5.3: End-to-End Tests
**Description**: Write end-to-end tests for complete user workflows.

**File**: `tests/e2e/test_workflows.py`

**Requirements**:
- Test complete user journeys
- Use real API (via TestClient or httpx)
- Test authentication flows
- Test multi-turn conversations
- Test memory persistence across sessions

**Example Workflows**:
1. **User Registration & First Conversation**:
   - Register user
   - Login and get token
   - Start conversation
   - Agent responds
   - Verify memory stored

2. **Multi-turn Conversation with Memory**:
   - Login
   - First message: "My favorite color is blue"
   - Second message: "What's my favorite color?"
   - Verify agent retrieves memory

3. **Tool Usage**:
   - Send prompt requiring tool use
   - Verify tool called
   - Verify correct response

4. **Error Handling**:
   - Invalid token
   - Malformed request
   - Verify appropriate errors returned

**Acceptance Criteria**:
- [ ] E2E tests for all major workflows
- [ ] Authentication flow tested
- [ ] Memory persistence tested
- [ ] Tool execution tested
- [ ] Error scenarios tested
- [ ] Tests use real API
- [ ] Can run against deployed instance

---

### Task 5.4: Documentation - API Documentation
**Description**: Create comprehensive API documentation.

**Files**:
- `docs/api/overview.md`
- `docs/api/authentication.md`
- `docs/api/agents.md`
- `docs/api/memory.md`
- `docs/api/errors.md`

**Requirements**:
- OpenAPI/Swagger auto-generated (via FastAPI)
- Additional documentation for:
  - Authentication flow
  - Example requests/responses
  - Error codes and meanings
  - Rate limiting
  - Best practices
- Use MkDocs Material for documentation site

**Example API Documentation**:
```markdown
# Agent Execution API

## Run Agent

Execute an agent with a prompt and receive a response.

**Endpoint**: `POST /agents/run`

**Authentication**: Required (JWT Bearer token)

**Request Body**:
```json
{
  "prompt": "What is the capital of France?",
  "session_id": "optional-session-id",
  "use_memory": true,
  "agent_config": {
    "temperature": 0.7
  }
}
```

**Response** (200 OK):
```json
{
  "response": "The capital of France is Paris.",
  "session_id": "abc-123-def",
  "metadata": {
    "model": "qwen2.5-14b-instruct",
    "duration_ms": 234.5
  },
  "tool_calls": [],
  "memory_stats": {
    "short_term_messages": 5,
    "long_term_retrieved": 2,
    "semantic_results": 1
  }
}
```

**Error Responses**:
- `401 Unauthorized`: Invalid or missing token
- `422 Validation Error`: Invalid request body
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Agent execution failed

**Rate Limits**: 60 requests per minute per user

**Example** (Python):
```python
import httpx

response = httpx.post(
    "http://localhost:8000/agents/run",
    headers={"Authorization": f"Bearer {token}"},
    json={"prompt": "Hello!"}
)

result = response.json()
print(result["response"])
```
```

**Acceptance Criteria**:
- [ ] OpenAPI spec generated and accessible
- [ ] Comprehensive markdown documentation
- [ ] All endpoints documented with examples
- [ ] Authentication flow explained
- [ ] Error codes documented
- [ ] MkDocs site generated
- [ ] Code examples in multiple languages

---

### Task 5.5: Documentation - Framework Guide
**Description**: Create developer guide for using and extending the framework.

**Files**:
- `docs/index.md`
- `docs/getting-started.md`
- `docs/architecture.md`
- `docs/agents.md`
- `docs/tools.md`
- `docs/memory.md`
- `docs/pipelines.md`
- `docs/deployment.md`
- `docs/best-practices.md`

**Requirements**:
- Clear getting started guide
- Architecture overview
- Component explanations
- Code examples
- Extension guides (custom agents, tools)
- Deployment guides
- Troubleshooting

**Table of Contents**:
```markdown
# MAI Framework Documentation

## Getting Started
- [Quick Start](getting-started.md)
- [Installation](installation.md)
- [Configuration](configuration.md)

## Core Concepts
- [Architecture Overview](architecture.md)
- [Agents](agents.md)
- [Tools](tools.md)
- [Memory Systems](memory.md)
- [Pipelines](pipelines.md)
- [Prompts](prompts.md)

## Guides
- [Creating Custom Agents](guides/custom-agents.md)
- [Building Tools](guides/building-tools.md)
- [Memory Management](guides/memory-management.md)
- [Pipeline Patterns](guides/pipeline-patterns.md)
- [Testing Strategies](guides/testing.md)

## Deployment
- [Local Development](deployment/local.md)
- [Docker Deployment](deployment/docker.md)
- [Production Best Practices](deployment/production.md)
- [Monitoring & Observability](deployment/monitoring.md)

## API Reference
- [API Documentation](api/overview.md)
- [Python SDK](api/python-sdk.md)

## Examples
- [Sentiment Analysis Agent](examples/sentiment-analysis.md)
- [Document Q&A System](examples/document-qa.md)
- [Content Moderation Pipeline](examples/content-moderation.md)

## Reference
- [Configuration Options](reference/configuration.md)
- [Error Codes](reference/errors.md)
- [Best Practices](reference/best-practices.md)
- [Troubleshooting](reference/troubleshooting.md)
```

**Acceptance Criteria**:
- [ ] Complete documentation site
- [ ] Getting started guide with working example
- [ ] Architecture documentation with diagrams
- [ ] Component guides with code examples
- [ ] Extension guides (custom agents, tools)
- [ ] Deployment documentation
- [ ] Best practices documented
- [ ] Troubleshooting guide

---

## PHASE 6: Deployment & DevOps

### Task 6.1: Docker Configuration
**Description**: Create production-ready Docker configuration.

**Files**:
- `deployment/docker/Dockerfile`
- `deployment/docker/docker-compose.yml`
- `deployment/docker/docker-compose.prod.yml`
- `deployment/docker/.dockerignore`

**Requirements**:
- Multi-stage Docker build
- Optimized image size
- Security best practices (non-root user, minimal base image)
- Health checks
- Docker Compose for local development
- Separate prod configuration

**Dockerfile Best Practices**:
```dockerfile
# Multi-stage build
FROM python:3.11-slim as builder
WORKDIR /build
RUN pip install poetry
COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY --from=builder /build/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Create non-root user
RUN useradd -m -u 1000 MAI && \
    chown -R MAI:MAI /app
USER MAI

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run
EXPOSE 8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Docker Compose** (Development):
```yaml
version: '3.8'

services:
  api:
    build:
      context: ../..
      dockerfile: deployment/docker/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://ultra:ultra@postgres:5432/MAI
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_URL=http://qdrant:6333
      - LM_STUDIO__BASE_URL=http://host.docker.internal:1234/v1
      - JWT_SECRET=dev-secret-change-in-production
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
      qdrant:
        condition: service_started
    volumes:
      - ../../src:/app/src  # Hot reload in dev
      - ../../config:/app/config

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      - POSTGRES_USER=ultra
      - POSTGRES_PASSWORD=ultra
      - POSTGRES_DB=MAI
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ultra"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
```

**Acceptance Criteria**:
- [ ] Multi-stage Dockerfile
- [ ] Optimized image size (<500MB)
- [ ] Non-root user
- [ ] Health check configured
- [ ] docker-compose.yml for development
- [ ] docker-compose.prod.yml for production
- [ ] .dockerignore file
- [ ] Documentation for Docker usage

---

### Task 6.2: Database Migrations
**Description**: Set up Alembic migrations and migration scripts.

**Files**:
- `alembic.ini`
- `src/infrastructure/database/migrations/env.py`
- `src/infrastructure/database/migrations/versions/001_initial.py`
- `scripts/migrate.py`

**Requirements**:
- Alembic configuration
- Initial migration with all tables
- Enable pgvector extension
- Migration helper scripts:
  - `migrate.py upgrade head` - Apply all migrations
  - `migrate.py downgrade` - Rollback migrations
  - `migrate.py revision` - Create new migration
- Automatic migration on startup (optional, configurable)

**Initial Migration**:
```python
"""Initial schema

Revision ID: 001_initial
Revises:
Create Date: 2025-11-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector

def upgrade():
    # Enable pgvector
    op.execute('CREATE EXTENSION IF NOT EXISTS vector;')

    # Users table
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Sessions table
    op.create_table(
        'sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_activity', sa.DateTime(timezone=True)),
    )

    # Memories table
    op.create_table(
        'memories',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('session_id', UUID(as_uuid=True), sa.ForeignKey('sessions.id')),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('embedding', Vector(1536)),  # Adjust dimension as needed
        sa.Column('metadata', JSONB, default={}),
        sa.Column('importance', sa.Float, default=0.5),
        sa.Column('access_count', sa.Integer, default=0),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Create indexes
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_sessions_user_id', 'sessions', ['user_id'])
    op.create_index('idx_memories_user_id', 'memories', ['user_id'])
    op.create_index('idx_memories_importance', 'memories', ['importance'])

def downgrade():
    op.drop_table('memories')
    op.drop_table('sessions')
    op.drop_table('users')
    op.execute('DROP EXTENSION IF EXISTS vector;')
```

**Acceptance Criteria**:
- [ ] Alembic configured
- [ ] Initial migration creates all tables
- [ ] pgvector extension enabled
- [ ] Migration scripts (upgrade, downgrade)
- [ ] Indexes for performance
- [ ] Documentation for migration workflow

---

### Task 6.3: Monitoring Setup
**Description**: Configure Prometheus metrics and monitoring.

**Files**:
- `src/core/utils/metrics.py`
- `deployment/prometheus/prometheus.yml`
- `deployment/grafana/dashboards/MAI.json`

**Requirements**:
- Prometheus client integration
- Custom metrics:
  - Counter: `MAI_requests_total{endpoint, method, status}`
  - Histogram: `MAI_request_duration_seconds{endpoint}`
  - Counter: `MAI_agent_executions_total{agent_name, status}`
  - Histogram: `MAI_agent_duration_seconds{agent_name}`
  - Counter: `MAI_tool_calls_total{tool_name, status}`
  - Gauge: `MAI_active_requests`
  - Gauge: `MAI_memory_records_total{user_id}`
- FastAPI middleware for automatic metrics
- Prometheus configuration
- Grafana dashboard (optional but recommended)

**Metrics Middleware**:
```python
from prometheus_client import Counter, Histogram, Gauge
from fastapi import Request
import time

REQUEST_COUNT = Counter(
    'MAI_requests_total',
    'Total requests',
    ['endpoint', 'method', 'status']
)

REQUEST_DURATION = Histogram(
    'MAI_request_duration_seconds',
    'Request duration',
    ['endpoint']
)

ACTIVE_REQUESTS = Gauge(
    'MAI_active_requests',
    'Active requests'
)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    ACTIVE_REQUESTS.inc()
    start_time = time.time()

    try:
        response = await call_next(request)

        # Record metrics
        REQUEST_COUNT.labels(
            endpoint=request.url.path,
            method=request.method,
            status=response.status_code
        ).inc()

        duration = time.time() - start_time
        REQUEST_DURATION.labels(endpoint=request.url.path).observe(duration)

        return response
    finally:
        ACTIVE_REQUESTS.dec()
```

**Prometheus Configuration**:
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'MAI'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
```

**Acceptance Criteria**:
- [ ] Prometheus client configured
- [ ] Custom metrics defined
- [ ] Metrics middleware for FastAPI
- [ ] `/metrics` endpoint exposing Prometheus format
- [ ] Prometheus configuration
- [ ] Grafana dashboard JSON (optional)
- [ ] Documentation for metrics

---

### Task 6.4: Logging Aggregation
**Description**: Configure centralized logging with structured output.

**Requirements**:
- JSON structured logging to stdout (for container logs)
- Log correlation IDs
- Log levels by environment (DEBUG in dev, INFO in prod)
- Optional Sentry integration for errors
- Log sampling for high-volume logs

**Enhanced Logging Setup**:
```python
import sys
from loguru import logger
from src.core.utils.config import settings
import sentry_sdk

def setup_logging():
    """Configure logging for the application"""

    # Remove default handler
    logger.remove()

    # Console (JSON for production, pretty for development)
    if settings.debug:
        # Pretty console logs for development
        logger.add(
            sys.stdout,
            level=settings.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[correlation_id]}</cyan> | <level>{message}</level>",
            colorize=True,
        )
    else:
        # JSON logs for production
        logger.add(
            sys.stdout,
            level=settings.log_level,
            format="{message}",
            serialize=True,  # JSON output
        )

    # File logs (always JSON)
    if settings.log_file:
        logger.add(
            settings.log_file,
            rotation="500 MB",
            retention="10 days",
            level="DEBUG",
            serialize=True,
            compression="zip",
        )

    # Sentry integration
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=0.1,
            environment="production" if not settings.debug else "development",
        )

    # Set correlation ID context
    logger.configure(extra={"correlation_id": "-"})

    return logger
```

**Correlation ID Middleware**:
```python
import uuid
from fastapi import Request

@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

    # Set in logger context
    with logger.contextualize(correlation_id=correlation_id):
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
```

**Acceptance Criteria**:
- [ ] JSON structured logging
- [ ] Correlation IDs in all logs
- [ ] Environment-specific log levels
- [ ] Sentry integration (conditional)
- [ ] Log rotation and compression
- [ ] Middleware for correlation IDs
- [ ] Documentation for log analysis

---

## PHASE 7: Example Implementation & Validation

### Task 7.1: Create Example Agent - Sentiment Analyzer
**Description**: Implement a complete example agent using the framework.

**Files**:
- `src/use_cases/sentiment_analyzer/agent.py`
- `src/use_cases/sentiment_analyzer/tools.py`
- `src/use_cases/sentiment_analyzer/prompts.py`
- `config/prompts/sentiment_analysis.yaml`
- `tests/integration/test_sentiment_agent.py`

**Requirements**:
- Complete implementation of sentiment analysis agent
- Custom tools for domain context
- Prompt template
- Result schema with Pydantic
- Integration test
- API endpoint

**Implementation**: Follow the example from the original framework document.

**Acceptance Criteria**:
- [ ] Sentiment analyzer agent implemented
- [ ] Tools registered
- [ ] Prompt template created
- [ ] Result validation works
- [ ] Integration test passes
- [ ] API endpoint functional
- [ ] Documentation with usage examples

---

### Task 7.2: Create Example Pipeline - Content Moderation
**Description**: Implement a multi-stage pipeline example.

**Files**:
- `src/use_cases/content_moderation/pipeline.py`
- `src/use_cases/content_moderation/stages.py`
- `src/use_cases/content_moderation/agents.py`
- `tests/integration/test_moderation_pipeline.py`

**Requirements**:
- Multi-stage pipeline:
  1. Toxicity detection
  2. PII detection
  3. Content sanitization
- Multiple agents
- Pipeline orchestration
- Integration test

**Implementation**: Follow the pipeline example from the original framework document.

**Acceptance Criteria**:
- [ ] Content moderation pipeline implemented
- [ ] All stages work independently
- [ ] Pipeline orchestration works
- [ ] Integration test passes
- [ ] Documentation with examples

---

### Task 7.3: Integration Validation & Smoke Tests
**Description**: Validate that all components work together correctly.

**File**: `tests/integration/test_full_system.py`

**Requirements**:
- End-to-end smoke tests
- Test all major components:
  - Configuration loading
  - Database connectivity
  - Redis connectivity
  - Qdrant connectivity
  - LM Studio connectivity
  - Agent execution
  - Memory storage and retrieval
  - Tool execution
  - Pipeline execution
  - API endpoints

**Smoke Test Example**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_system_smoke():
    """Smoke test for entire system"""

    # 1. Check configuration
    assert settings.lm_studio.base_url == "http://localhost:1234/v1"

    # 2. Check database
    async with get_db() as db:
        result = await db.execute("SELECT 1")
        assert result.scalar() == 1

    # 3. Check Redis
    cache = RedisClient()
    await cache.set("test", "value")
    assert await cache.get("test") == "value"

    # 4. Check Qdrant
    qdrant = QdrantClient()
    collections = await qdrant.list_collections()
    assert "MAI_memories" in collections

    # 5. Check LM Studio
    models = await get_available_models(settings.lm_studio.base_url)
    assert len(models) > 0

    # 6. Test agent execution
    agent = SentimentAnalyzerAgent()
    result = await agent.run("This is great!")
    assert result.sentiment == "positive"

    # 7. Test API
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
```

**Acceptance Criteria**:
- [ ] Smoke tests for all components
- [ ] End-to-end workflow test
- [ ] All tests pass in fresh environment
- [ ] Clear error messages for failures
- [ ] Documentation for running tests

---

### Task 7.4: Performance Testing
**Description**: Basic performance testing and optimization.

**File**: `tests/performance/test_load.py`

**Requirements**:
- Load testing for API endpoints
- Memory leak detection
- Database query optimization
- Tool for performance testing (locust or pytest-benchmark)

**Example Load Test**:
```python
from locust import HttpUser, task, between

class MAIUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Login
        response = self.client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        self.token = response.json()["access_token"]

    @task(3)
    def run_agent(self):
        self.client.post(
            "/agents/run",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"prompt": "Hello, how are you?"}
        )

    @task(1)
    def search_memory(self):
        self.client.get(
            "/memory/search",
            headers={"Authorization": f"Bearer {self.token}"},
            params={"query": "test", "limit": 5}
        )
```

**Performance Goals** (for small scale):
- API latency p95 < 500ms (excluding LLM)
- Database queries < 10ms
- Memory operations < 50ms
- Support 10 concurrent users without degradation

**Acceptance Criteria**:
- [ ] Load testing setup (Locust or similar)
- [ ] Performance benchmarks documented
- [ ] Database queries optimized (indexes, N+1 prevention)
- [ ] Memory leaks checked
- [ ] Performance goals met or documented

---

## PHASE 8: Polish & Documentation

### Task 8.1: Code Quality & Linting
**Description**: Set up linting, formatting, and code quality tools.

**Files**:
- `.pre-commit-config.yaml`
- `pyproject.toml` (tool configuration)
- `.github/workflows/ci.yml` (if using GitHub)

**Requirements**:
- Tools:
  - Black (code formatting)
  - isort (import sorting)
  - Ruff (fast linting)
  - mypy (type checking)
  - pre-commit hooks
- CI/CD integration

**Configuration**:
```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 100

[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "W", "I", "N", "UP", "ANN", "B", "A", "C4", "DTZ", "T10", "EXE", "ISC", "ICN", "G", "PIE", "T20", "PYI", "PT", "Q", "RSE", "RET", "SLF", "SIM", "TID", "TCH", "ARG", "PTH", "ERA", "PD", "PGH", "PL", "TRY", "NPY", "RUF"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

**Pre-commit Configuration**:
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.12.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

**Acceptance Criteria**:
- [ ] Black configured and applied
- [ ] isort configured
- [ ] Ruff linting passing
- [ ] mypy type checking passing
- [ ] Pre-commit hooks installed
- [ ] CI/CD runs checks
- [ ] All code formatted consistently

---

### Task 8.2: Security Audit
**Description**: Security review and hardening.

**Requirements**:
- Dependency vulnerability scanning (Safety, Snyk)
- SQL injection prevention review
- XSS prevention review
- CSRF protection
- Rate limiting review
- Secrets management review
- Docker security review

**Security Checklist**:
- [ ] No hardcoded secrets in code
- [ ] Environment variables for all secrets
- [ ] SQL injection: Using ORM (SQLAlchemy) with bound parameters
- [ ] XSS: FastAPI auto-escapes responses
- [ ] CSRF: Token validation for state-changing operations
- [ ] Rate limiting: Implemented for auth and API endpoints
- [ ] Password hashing: Bcrypt with cost factor 12
- [ ] JWT: Proper secret, expiration, validation
- [ ] Docker: Non-root user, minimal base image
- [ ] Dependencies: No known vulnerabilities (run `safety check`)
- [ ] Input validation: Pydantic models for all inputs
- [ ] HTTPS in production (documented)
- [ ] CORS: Configured appropriately

**Tools**:
```bash
# Dependency scanning
poetry run safety check

# Docker image scanning
docker scan MAI:latest

# OWASP dependency check (optional)
```

**Acceptance Criteria**:
- [ ] Security checklist completed
- [ ] No high-severity vulnerabilities
- [ ] Security best practices documented
- [ ] Dependency scanning in CI/CD
- [ ] Docker image scanning passing

---

### Task 8.3: README & Quick Start
**Description**: Create comprehensive README with quick start guide.

**File**: `README.md`

**Requirements**:
- Project overview
- Features list
- Quick start guide (5 minutes to running)
- Prerequisites
- Installation steps
- Configuration
- Usage examples
- Documentation links
- Contributing guide
- License

**README Structure**:
```markdown
# MAI

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Production-ready AI application framework built on Pydantic AI.

## Features

- 🤖 **Type-Safe Agents**: Built on Pydantic AI with full type safety
- 🧠 **Comprehensive Memory**: Short-term, long-term, and semantic memory
- 🔧 **Tool System**: Extensible tool system with decorators
- 🔗 **Pipelines**: Chain agents and tools in complex workflows
- 📊 **Observability**: Built-in logging, metrics, and tracing
- 🔒 **Security**: JWT authentication, rate limiting, input validation
- 🐳 **Docker-Ready**: Production-ready containers and Docker Compose
- 📚 **Well-Documented**: Comprehensive documentation and examples

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- LM Studio (running locally on port 1234)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/MAI.git
cd MAI

# Install dependencies
poetry install

# Copy environment file
cp .env.example .env

# Edit .env with your settings
# JWT_SECRET is required!

# Start infrastructure
docker-compose up -d postgres redis qdrant

# Run migrations
poetry run alembic upgrade head

# Start API
poetry run uvicorn src.api.main:app --reload
```

### First Request

```python
import httpx

# Register user
response = httpx.post("http://localhost:8000/auth/register", json={
    "email": "user@example.com",
    "password": "securepassword"
})
token = response.json()["access_token"]

# Run agent
response = httpx.post(
    "http://localhost:8000/agents/run",
    headers={"Authorization": f"Bearer {token}"},
    json={"prompt": "Hello! What can you help me with?"}
)

print(response.json()["response"])
```

## Documentation

- [Full Documentation](https://MAI.readthedocs.io)
- [API Reference](docs/api/overview.md)
- [Architecture](docs/architecture.md)
- [Examples](docs/examples/)

## Examples

- [Sentiment Analysis Agent](src/use_cases/sentiment_analyzer/)
- [Content Moderation Pipeline](src/use_cases/content_moderation/)

## Development

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src

# Type checking
poetry run mypy src

# Linting
poetry run ruff check src

# Format code
poetry run black src
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT License - see [LICENSE](LICENSE)
```

**Acceptance Criteria**:
- [ ] README.md comprehensive and clear
- [ ] Quick start works in <5 minutes
- [ ] All badges/links working
- [ ] Examples included
- [ ] Contributing guide
- [ ] License file

---

### Task 8.4: Final Integration Test & Demo Script
**Description**: Create demo script showing framework capabilities.

**File**: `scripts/demo.py`

**Requirements**:
- Interactive demo script
- Shows all major features:
  - Agent execution
  - Memory persistence
  - Tool usage
  - Multi-turn conversation
  - Pipeline execution
- Can be run after quick start

**Demo Script Example**:
```python
#!/usr/bin/env python3
"""
MAI Framework Demo

This script demonstrates the key features of the MAI framework.
"""

import asyncio
import httpx
from rich.console import Console
from rich.panel import Panel

console = Console()

async def main():
    console.print(Panel.fit("MAI Framework Demo", style="bold magenta"))

    base_url = "http://localhost:8000"

    # 1. Health Check
    console.print("\n[bold cyan]1. Health Check[/bold cyan]")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/health")
        console.print(response.json())

    # 2. Register & Login
    console.print("\n[bold cyan]2. User Registration & Login[/bold cyan]")
    async with httpx.AsyncClient() as client:
        # Register
        response = await client.post(f"{base_url}/auth/register", json={
            "email": "demo@MAI.ai",
            "password": "demo_password_123"
        })
        token = response.json()["access_token"]
        console.print(f"✓ Registered and received token")

    headers = {"Authorization": f"Bearer {token}"}

    # 3. First Agent Interaction
    console.print("\n[bold cyan]3. First Agent Interaction[/bold cyan]")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/agents/run",
            headers=headers,
            json={"prompt": "My name is Alice and I love Python programming."}
        )
        result = response.json()
        console.print(f"Agent: {result['response']}")
        session_id = result['session_id']

    # 4. Memory Retrieval
    console.print("\n[bold cyan]4. Memory Retrieval[/bold cyan]")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/agents/run",
            headers=headers,
            json={
                "prompt": "What's my name and what do I like?",
                "session_id": session_id
            }
        )
        result = response.json()
        console.print(f"Agent: {result['response']}")
        console.print(f"Memory Stats: {result['memory_stats']}")

    # 5. Tool Usage Example
    console.print("\n[bold cyan]5. Tool Usage[/bold cyan]")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/agents/run",
            headers=headers,
            json={"prompt": "Search for information about Pydantic AI"}
        )
        result = response.json()
        if result['tool_calls']:
            console.print(f"Tools Called: {[t['tool_name'] for t in result['tool_calls']]}")
        console.print(f"Agent: {result['response']}")

    # 6. Semantic Memory Search
    console.print("\n[bold cyan]6. Semantic Memory Search[/bold cyan]")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{base_url}/memory/search",
            headers=headers,
            params={"query": "programming languages", "limit": 3}
        )
        memories = response.json()
        console.print(f"Found {len(memories)} relevant memories:")
        for mem in memories:
            console.print(f"  - {mem['content'][:50]}...")

    console.print("\n[bold green]✓ Demo Complete![/bold green]")
    console.print("\nExplore more:")
    console.print("  - API Docs: http://localhost:8000/docs")
    console.print("  - Documentation: ./docs/")

if __name__ == "__main__":
    asyncio.run(main())
```

**Acceptance Criteria**:
- [ ] Demo script runs successfully
- [ ] Shows all major features
- [ ] Clear output with rich formatting
- [ ] Can be run immediately after quick start
- [ ] Documented in README

---

## Task Organization in Archon

**CRITICAL**: Before starting implementation, you MUST create a project and all tasks in Archon using the MCP tools.

### Project Structure in Archon:

**Project**: "MAI Framework Implementation"
- **Description**: "Build production-ready AI application framework on Pydantic AI with comprehensive memory, tools, and observability"
- **Features to track**:
  - Core Framework (agents, tools, memory, pipelines)
  - Infrastructure (database, Redis, Qdrant, LM Studio)
  - API Layer (FastAPI, authentication, endpoints)
  - Testing (unit, integration, e2e)
  - Deployment (Docker, monitoring, logging)
  - Documentation (API docs, guides, examples)

### Task Creation Workflow:

1. **Create Project** using `mcp__archon__manage_project`
2. **Create Tasks** for each task above using `mcp__archon__manage_task`
   - Use descriptive titles from task headers
   - Include full description from "Requirements" section
   - Set appropriate `task_order` (priority)
   - Assign to "Coding Agent"
   - Group by `feature` (e.g., "Core Framework", "Infrastructure", etc.)

### Example Task Creation:
```json
{
  "action": "create",
  "project_id": "<project_id>",
  "title": "Initialize Project Structure",
  "description": "Create complete directory structure and initialize Python project with Poetry. Requirements: Create all directories, initialize pyproject.toml with dependencies, create .env.example, .gitignore, and README.md",
  "status": "todo",
  "assignee": "Coding Agent",
  "feature": "Project Setup",
  "task_order": 100
}
```

---

## Implementation Checklist

Before starting implementation, ensure:

- [ ] Read and understand this entire document
- [ ] Review Pydantic AI documentation in Archon knowledge base (source_id: `473e7956a86382e6`)
- [ ] LM Studio is running and accessible at `http://localhost:1234`
- [ ] Docker and Docker Compose installed
- [ ] Python 3.11+ installed
- [ ] Created project in Archon
- [ ] Created all tasks in Archon with proper organization
- [ ] Understand the architecture and component relationships

---

## Key Design Decisions

### 1. Single Model Strategy
- Use one LM Studio model for all tasks (simplifies configuration)
- Model selection via `/v1/models` endpoint on startup
- Configurable timeout and retry settings

### 2. Memory Architecture
- **Short-term**: Redis-backed conversation history (10 messages, token-limited)
- **Long-term**: PostgreSQL + pgvector for persistent storage
- **Semantic**: Qdrant for fast vector search on memories
- Integration: All three work together for comprehensive context

### 3. Authentication
- JWT tokens (stateless, good for small scale)
- Token blacklisting via Redis (for logout)
- Bcrypt for password hashing (cost factor 12)
- Per-user rate limiting

### 4. Tool System
- Global registry for easy discovery
- Decorator-based registration
- Category organization
- Retry, timeout, cache decorators

### 5. Pipeline System
- Sequential execution by default
- Optional parallel for independent stages
- DAG support for complex dependencies
- Error strategies: fail-fast, continue, retry

---

## Common Pitfalls to Avoid

1. **Generic Types**: Don't use unused generic type parameters (BaseAgentFramework[T, ResultT] where T is never used)

2. **Incomplete Implementations**: No `pass` statements in production code - implement all methods

3. **Hard-coded Values**: Use configuration for all environment-specific values

4. **Missing Error Handling**: Every external call (DB, Redis, Qdrant, LM Studio) needs try/catch

5. **Security**: Never log secrets, use environment variables, validate all inputs

6. **Memory Leaks**: Close database sessions, Redis connections, HTTP clients

7. **Blocking Operations**: Use async/await consistently, don't block event loop

8. **Testing**: Don't skip tests - they catch issues early

---

## Success Criteria

The implementation is complete when:

- [ ] All 40+ tasks completed and marked as "done" in Archon
- [ ] All tests pass (unit, integration, e2e)
- [ ] Code quality checks pass (black, ruff, mypy)
- [ ] Documentation complete and renders correctly
- [ ] Demo script runs successfully
- [ ] Docker containers build and run
- [ ] Quick start guide works (<5 minutes to running system)
- [ ] All components integrated and working together
- [ ] Security checklist completed
- [ ] Performance goals met
- [ ] No high-severity vulnerabilities

---

## Next Steps

1. **Review this document completely**
2. **Create Archon project and all tasks**
3. **Start with Phase 1: Project Setup & Foundation**
4. **Follow tasks sequentially within each phase**
5. **Mark tasks complete in Archon as you finish**
6. **Test continuously (don't wait until end)**
7. **Document as you build**
8. **Ask for clarification if needed**

---

## Support & Resources

- **Pydantic AI Docs**: Use Archon knowledge base (source_id: `473e7956a86382e6`)
- **FastAPI Docs**: Use Archon knowledge base (source_id: `c889b62860c33a44`)
- **LM Studio**: http://localhost:1234 (should be running)
- **This Document**: Reference throughout implementation

---

## Notes

- This is a **comprehensive, production-ready** implementation
- Estimated effort: 40-60 hours for full implementation
- Can be built incrementally (phase by phase)
- Each phase builds on the previous
- All code should be type-safe, tested, and documented
- Focus on quality over speed

**Good luck! Build something amazing with MAI!** 🚀
