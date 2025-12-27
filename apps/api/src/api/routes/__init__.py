"""Route initialization module."""

from api.routes.chat import router as chat_router
from api.routes.health import router as health_router
from api.routes.user import router as user_router
from fastapi import APIRouter

# Create main API router
api_router = APIRouter(prefix="/api")


# Include sub-routers
api_router.include_router(health_router)
api_router.include_router(user_router)

# Include chat router at root level (no /api prefix for v1 routes)
chat_router_no_prefix = APIRouter()
chat_router_no_prefix.include_router(chat_router)


__all__ = ["api_router", "chat_router_no_prefix"]
