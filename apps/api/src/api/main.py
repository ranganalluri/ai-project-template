"""Main FastAPI application."""

import logging

from fastapi import FastAPI

from src.api.config import get_settings
from src.api.middleware import setup_middleware
from src.api.routes import api_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize settings
settings = get_settings()

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Agentic AI - FastAPI backend service",
    version=settings.app_version,
)

# Setup middleware
setup_middleware(app, ui_url=settings.ui_url)

# Include routers
app.include_router(api_router)


@app.on_event("startup")
async def startup_event() -> None:
    """Handle startup event."""
    logger.info(f"{settings.app_name} v{settings.app_version} started")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Log level: {settings.log_level}")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Handle shutdown event."""
    logger.info(f"{settings.app_name} shutting down")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
