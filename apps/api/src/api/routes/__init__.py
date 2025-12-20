"""Route initialization module."""

from fastapi import APIRouter


from api.routes.health import router as health_router
from api.routes.user import router as user_router

# Create main API router
api_router = APIRouter(prefix="/api")


# Include sub-routers
api_router.include_router(health_router)
api_router.include_router(user_router)


__all__ = ["api_router"]
