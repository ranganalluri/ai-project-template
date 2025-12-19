"""Main FastAPI application."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.config import get_settings
from api.middleware import setup_middleware
from api.routes import api_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Handle application lifespan events."""
    # Startup
    logger.info(f"{settings.app_name} v{settings.app_version} started")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Log level: {settings.log_level}")

    yield

    # Shutdown
    logger.info(f"{settings.app_name} shutting down")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Agentic AI - FastAPI backend service",
    version=settings.app_version,
    lifespan=lifespan,
)

# Setup middleware
setup_middleware(app, ui_url=settings.ui_url)

# Include routers
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
