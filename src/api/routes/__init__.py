from fastapi import APIRouter

from . import agents
from . import tools

api_router = APIRouter()
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])
