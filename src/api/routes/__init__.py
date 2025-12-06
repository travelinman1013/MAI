from fastapi import APIRouter

from . import agents
from . import documents
from . import models
from . import tools

api_router = APIRouter()
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(models.router, tags=["models"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])
