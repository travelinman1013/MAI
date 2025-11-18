# MAI Framework

Production-ready AI application framework built on Pydantic AI, designed for building reliable, type-safe AI agents with comprehensive memory management, tool orchestration, and enterprise-grade observability.

## Features

- **Type-Safe AI Agents**: Built on Pydantic AI for robust, validated agent interactions
- **Comprehensive Memory Management**: Short-term (Redis), long-term (PostgreSQL+pgvector), and semantic search (Qdrant)
- **Extensible Tool System**: Decorator-based tool registration with automatic retry, timeout, caching, and rate limiting
- **Pipeline Orchestration**: Sequential, parallel, and DAG-based execution with configurable error handling
- **Production-Ready Authentication**: JWT tokens with bcrypt password hashing and Redis-based token blacklisting
- **Full Observability**: Prometheus metrics, structured logging (Loguru), and optional Sentry integration
- **LM Studio Integration**: Local OpenAI-compatible LLM server support

## Quick Start

### Prerequisites

- Python 3.11+
- Poetry
- PostgreSQL (with pgvector extension)
- Redis
- Qdrant
- LM Studio (running at http://localhost:1234)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ai_framework_1
```

2. Install dependencies with Poetry:
```bash
poetry install
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Set up the database:
```bash
# Install pgvector extension in PostgreSQL
# Run migrations
poetry run alembic upgrade head
```

5. Start the development server:
```bash
poetry run uvicorn src.api.main:app --reload
```

### Configuration

Key environment variables (see `.env.example` for full list):

- `LM_STUDIO__BASE_URL`: LM Studio API endpoint (default: http://localhost:1234/v1)
- `DATABASE_URL`: PostgreSQL connection string with asyncpg driver
- `REDIS_URL`: Redis connection string
- `QDRANT_URL`: Qdrant vector database URL
- `JWT_SECRET`: Secret key for JWT token signing (change in production!)

## Project Structure

```
src/
├── core/               # Core framework components
│   ├── agents/        # Agent base classes and implementations
│   ├── tools/         # Tool system (registry, decorators, base)
│   ├── memory/        # Memory management (short-term, long-term, semantic)
│   ├── prompts/       # Prompt templates and registry
│   ├── pipeline/      # Pipeline orchestration
│   ├── models/        # LM Studio provider integration
│   └── utils/         # Utilities (config, logging, exceptions, auth, metrics)
├── infrastructure/    # Infrastructure layer
│   ├── database/      # Database session, models, migrations
│   ├── cache/         # Redis client
│   └── vector_store/  # Qdrant client
├── api/              # FastAPI application
│   ├── routes/       # API endpoints (health, auth, agents, memory)
│   └── middleware/   # Custom middleware (auth, rate limiting, etc.)
└── use_cases/        # Example use cases
    ├── sentiment_analyzer/
    └── content_moderation/
```

## Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run unit tests only
poetry run pytest -m unit

# Run with coverage
poetry run pytest --cov=src --cov-report=html
```

### Code Quality

```bash
# Format code
poetry run black src tests

# Lint code
poetry run ruff check src tests

# Type checking
poetry run mypy src
```

### Pre-commit Hooks

```bash
poetry run pre-commit install
poetry run pre-commit run --all-files
```

## API Documentation

Once the server is running, access the interactive API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

[Add license information]

## Contributing

[Add contributing guidelines]
