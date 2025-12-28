"""Main FastAPI application."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from api.config import get_settings
from api.middleware import get_cors_headers, setup_middleware
from api.routes import api_router, chat_router_no_prefix
from api.services.cosmos_db_init import initialize_cosmos_db
from fastapi import FastAPI, Request, status
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

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

    # Initialize Cosmos DB
    logger.info("Initializing Cosmos DB...")
    await initialize_cosmos_db(settings)

    yield

    # Shutdown
    logger.info(f"{settings.app_name} shutting down")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Agentic AI - FastAPI backend service",
    version=settings.app_version,
    lifespan=lifespan,
    redirect_slashes=False,
)

# Setup middleware (must be before exception handlers)
setup_middleware(app, ui_url=settings.ui_url, environment=settings.environment)


# Exception handler to ensure CORS headers are present on all error responses
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler to ensure CORS headers are present on all errors."""
    # Let FastAPI handle HTTPException normally (CORS middleware handles it)
    if isinstance(exc, HTTPException):
        raise exc

    logger.error("Unhandled exception: %s", exc, exc_info=True)

    # Get CORS headers using shared function
    origin = request.headers.get("origin")
    cors_headers = get_cors_headers(origin, ui_url=settings.ui_url, environment=settings.environment)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)},
        headers=cors_headers,
    )


# Include routers
app.include_router(api_router)
app.include_router(chat_router_no_prefix)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
