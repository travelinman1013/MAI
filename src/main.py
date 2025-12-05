from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.api.routes import api_router
from src.core.agents.registry import agent_registry
from src.core.agents.simple_agent import SimpleAgent
from src.core.tools import examples as tool_examples  # Import to register tools
from src.core.tools.registry import tool_registry

# Service connection status tracking
_service_status = {
    "redis": False,
    "postgresql": False,
    "qdrant": False,
}


async def _init_redis() -> bool:
    """Initialize Redis connection. Returns True if successful."""
    try:
        from src.infrastructure.cache.redis_client import RedisClient
        client = RedisClient()
        await client.connect()
        await client.disconnect()  # Just testing connectivity
        print("Startup: Redis connected successfully")
        return True
    except Exception as e:
        print(f"Startup: Redis unavailable (optional): {e}")
        return False


async def _init_postgresql() -> bool:
    """Initialize PostgreSQL connection. Returns True if successful."""
    try:
        from src.infrastructure.database.session import init_db, close_db, get_engine
        from sqlalchemy import text

        init_db()
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        print("Startup: PostgreSQL connected successfully")
        return True
    except Exception as e:
        print(f"Startup: PostgreSQL unavailable (optional): {e}")
        return False


async def _init_qdrant() -> bool:
    """Initialize Qdrant connection. Returns True if successful."""
    try:
        from qdrant_client import QdrantClient
        from src.core.utils.config import get_settings

        settings = get_settings()
        client = QdrantClient(url=settings.qdrant.url)
        client.get_collections()
        print("Startup: Qdrant connected successfully")
        return True
    except Exception as e:
        print(f"Startup: Qdrant unavailable (optional): {e}")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _service_status

    # Register agents on startup
    agent_registry.register_agent(SimpleAgent)
    print(f"Startup: Agents registered ({len(agent_registry.list_agents())} agents)")

    # Tools are auto-registered when imported
    tool_count = len(tool_registry.list_all_tools())
    print(f"Startup: Tools registered ({tool_count} tools)")

    # Initialize optional services (failures are logged but don't crash the app)
    _service_status["redis"] = await _init_redis()
    _service_status["postgresql"] = await _init_postgresql()
    _service_status["qdrant"] = await _init_qdrant()

    # Log service summary
    connected = [svc for svc, status in _service_status.items() if status]
    disconnected = [svc for svc, status in _service_status.items() if not status]
    print(f"Startup: Services connected: {connected or 'none'}")
    if disconnected:
        print(f"Startup: Services unavailable (optional): {disconnected}")

    yield

    # Clean up on shutdown
    try:
        from src.infrastructure.database.session import close_db
        await close_db()
    except Exception:
        pass

    try:
        from src.infrastructure.cache.redis_client import close_redis_client
        await close_redis_client()
    except Exception:
        pass

    print("Shutdown: Application shutting down.")

app = FastAPI(
    title="MAI Framework API",
    description="API for interacting with MAI Framework agents and services.",
    version="0.0.1",
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "MAI Framework API is running!"}


@app.get("/health")
async def health():
    """Health check endpoint with service status."""
    return {
        "status": "healthy",
        "services": _service_status,
    }
