"""Main FastAPI application."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from api.config import get_settings
from api.middleware import get_cors_headers, setup_middleware
from api.routes import api_router, chat_router_no_prefix
from api.services.cosmos_db_init import initialize_cosmos_db
from fastapi import FastAPI, Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Disable Cosmos DB INFO logging (only show WARNING and above)
logging.getLogger("azure.cosmos").setLevel(logging.WARNING)
logging.getLogger("azure.cosmos._cosmos_http_logging_policy").setLevel(logging.WARNING)

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


# Request validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors with detailed logging."""
    errors = exc.errors()
    logger.error("Request validation error on %s %s", request.method, request.url.path)
    for error in errors:
        logger.error("Validation error: %s", error)
    
    # Try to log request body if available
    try:
        body = await request.body()
        if body:
            logger.error("Request body: %s", body.decode("utf-8", errors="replace")[:500])
    except Exception:
        pass
    
    # Get CORS headers
    origin = request.headers.get("origin")
    cors_headers = get_cors_headers(origin, ui_url=settings.ui_url, environment=settings.environment)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": errors,
            "body": str(exc.body) if hasattr(exc, "body") else None,
        },
        headers=cors_headers,
    )


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
