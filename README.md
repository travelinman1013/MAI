# VERSION 2.0 (MLX BASED) HERE: https://github.com/travelinman1013/MAI-v2

# MAI Framework

A local-first AI agent framework built on Pydantic AI. 

## What This Is

MAI (My AI) is a personal AI framework that keeps everything local:
- **Local LLM inference** via LM Studio (no API costs, full privacy)
- **Local vector search** via Qdrant (semantic memory)
- **Local database** via PostgreSQL (conversations, users)
- **Local caching** via Redis (session memory)

## Current Status

| Component | Status |
|-----------|--------|
| FastAPI backend | Working |
| Gradio chat UI | Working (enhanced) |
| Redis caching | Working |
| LM Studio integration | Working (with model switching) |
| PostgreSQL database | Configured (run prompts to set up) |
| Qdrant vector store | Configured (run prompts to set up) |
| Conversation memory | Working |
| Image support | Working (multimodal chat) |
| Document upload | Working (PDF/TXT/MD) |
| Custom theme | Working |
| RAG pipeline | Planned |

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [LM Studio](https://lmstudio.ai/) running on port 1234 with a model loaded

### Run with Docker Compose

```bash
# Clone and enter directory
git clone <repository-url>
cd MAI

# Copy environment file
cp .env.example .env

# Start all services
docker compose up -d

# Wait for services to be healthy (~30 seconds)
docker compose ps
```

### Access the Application

| Service | URL | Description |
|---------|-----|-------------|
| Chat UI | http://localhost:7860 | Gradio chat interface |
| API | http://localhost:8000 | FastAPI backend |
| API Docs | http://localhost:8000/docs | Swagger documentation |
| Health | http://localhost:8000/health | Service status |

### Test It

1. Make sure LM Studio is running with a model loaded
2. Open http://localhost:7860
3. Start chatting

## Features

### Enhanced Chat Interface

The Gradio frontend provides a polished chat experience with:

- **Custom Visual Theme** - Modern, clean interface with custom colors and styling
- **Model Switching** - Switch between LM Studio models without restarting
- **Multimodal Input** - Upload images for vision-enabled models
- **Document Context** - Upload PDF, TXT, or MD files to inject context
- **Session Management** - Save, load, and switch between conversation sessions
- **Real-time Status** - Connection status and service health monitoring

### Keyboard Shortcuts

- **Enter** - Send message
- **Shift+Enter** - New line in message

### Document Upload

Upload documents to provide context to the AI:

1. Click the "Document" tab in the attachment area
2. Upload a PDF, TXT, or MD file (up to 10MB)
3. The content is extracted and injected into your next message
4. Supports automatic truncation for large documents (50,000 character limit)

Supported formats:
- **PDF** - Text extraction from PDF documents
- **TXT** - Plain text files
- **MD/Markdown** - Markdown documents

### Image Support

For vision-enabled models:

1. Click the "Image" tab in the attachment area
2. Upload or paste an image (up to 5MB)
3. Ask questions about the image
4. Supports: JPG, PNG, GIF, WebP

### Model Management

Switch between different LM Studio models:

1. Select a model from the "Model" dropdown
2. The model will be loaded in LM Studio automatically
3. Continue chatting with the new model

### Configuration

GUI settings can be configured via environment variables:

```bash
# GUI Configuration
GUI_API_BASE_URL=http://localhost:8000/api/v1
GUI_DEFAULT_AGENT=chat_agent
GUI_APP_TITLE="MAI Chat Interface"
GUI_SERVER_PORT=7860

# Feature limits
GUI_MAX_DOCUMENT_SIZE_MB=10
GUI_MAX_IMAGE_SIZE_MB=5

# Feature flags
GUI_ENABLE_MODEL_SWITCHING=true
GUI_SHOW_DEBUG_INFO=false
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         MAI Framework                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌──────────────┐         ┌──────────────┐                 │
│   │  Gradio UI   │────────▶│  FastAPI     │                 │
│   │  :7860       │         │  :8000       │                 │
│   └──────────────┘         └──────┬───────┘                 │
│                                   │                          │
│                    ┌──────────────┼──────────────┐          │
│                    ▼              ▼              ▼          │
│             ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│             │  Redis   │  │ Postgres │  │  Qdrant  │        │
│             │  :6379   │  │  :5432   │  │  :6333   │        │
│             └──────────┘  └──────────┘  └──────────┘        │
│                                                              │
│                    ┌──────────────────────────┐             │
│                    │       LM Studio          │             │
│                    │    host.docker.internal  │             │
│                    │         :1234            │             │
│                    └──────────────────────────┘             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

Edit `.env` to customize:

```bash
# LLM Provider (lmstudio, openai, or auto)
LLM__PROVIDER=lmstudio
LM_STUDIO__BASE_URL=http://host.docker.internal:1234/v1
LM_STUDIO__MODEL_NAME=your-model-name

# Or use OpenAI
# LLM__PROVIDER=openai
# OPENAI__API_KEY=sk-...
# OPENAI__MODEL=gpt-4o-mini
```

## Project Structure

```
MAI/
├── src/
│   ├── api/              # FastAPI routes
│   ├── core/
│   │   ├── agents/       # ChatAgent, SimpleAgent
│   │   ├── memory/       # Short-term, long-term, context management
│   │   ├── tools/        # Tool registry and decorators
│   │   └── utils/        # Config, logging, exceptions
│   ├── gui/              # Gradio chat interface
│   └── infrastructure/
│       ├── cache/        # Redis client
│       ├── database/     # SQLAlchemy models, migrations
│       └── vector_store/ # Qdrant client
├── prompts/              # Sequential setup prompts (run these!)
├── docker-compose.yml    # Container orchestration
├── Dockerfile            # API container
├── Dockerfile.gui        # GUI container
└── pyproject.toml        # Python dependencies
```

## Setting Up PostgreSQL + Qdrant

The database and vector store need one-time setup. Run the prompts in order:

```bash
# Each prompt is a self-contained task for Claude Code
prompts/01-docker-services.md    # Add postgres + qdrant to docker-compose
prompts/02-environment-config.md # Configure environment variables
prompts/03-database-migrations.md # Create database tables
prompts/04-service-integration.md # Wire up connections
prompts/05-seed-testing.md        # Add test data
```

## Development

### Local Development (without Docker)

```bash
# Install dependencies
poetry install

# Start services manually (Redis required, others optional)
# Redis: brew install redis && redis-server
# Or use Docker for services: docker compose up redis postgres qdrant -d

# Run API
poetry run uvicorn src.main:app --reload --port 8000

# Run GUI (in another terminal)
poetry run python -m src.gui.app
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src

# Run frontend integration tests
poetry run pytest tests/gui/test_frontend_integration.py -v

# Run the full frontend test suite
./scripts/test_frontend.sh
```

### Code Quality

```bash
poetry run black src tests
poetry run ruff check src tests
poetry run mypy src
```

## Roadmap

Building toward a private NotebookLM:

1. **Infrastructure** - PostgreSQL, Qdrant, Redis (current)
2. **Document Ingestion** - PDF, DOCX, URL processing
3. **Notebook Abstraction** - Collections with scoped context
4. **Grounded RAG** - Retrieval-augmented chat with citations
5. **Studio Outputs** - Summaries, flashcards, quizzes

## License

MIT
