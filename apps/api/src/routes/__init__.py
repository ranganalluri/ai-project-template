"""Route initialization module."""

from fastapi import APIRouter
from src.routes.health import router as health_router

# Create main API router
api_router = APIRouter(prefix="/api")

# Include sub-routers
api_router.include_router(health_router)


__all__ = ["api_router"]
