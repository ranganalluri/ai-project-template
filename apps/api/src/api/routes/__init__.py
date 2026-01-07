"""Route initialization module."""

from api.routes.chat import router as chat_router
from api.routes.content_processing import router as content_processing_router
from api.routes.health import router as health_router
from api.routes.user import router as user_router
from fastapi import APIRouter

# Create main API router
api_router = APIRouter(prefix="/api", redirect_slashes=False)


# Include sub-routers
api_router.include_router(health_router)
api_router.include_router(user_router)

# Include chat router at root level (no /api prefix for v1 routes)
chat_router_no_prefix = APIRouter(redirect_slashes=False)
chat_router_no_prefix.include_router(chat_router)
chat_router_no_prefix.include_router(content_processing_router)


__all__ = ["api_router", "chat_router_no_prefix"]
