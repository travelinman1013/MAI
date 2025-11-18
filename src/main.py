from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.api.routes import api_router
from src.core.agents.registry import agent_registry
from src.core.agents.simple_agent import SimpleAgent

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register agents on startup
    agent_registry.register_agent(SimpleAgent)
    print("Startup: Agents registered.")
    yield
    # Clean up on shutdown (if any)
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
