from fastapi import APIRouter

from . import agents

api_router = APIRouter()
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
