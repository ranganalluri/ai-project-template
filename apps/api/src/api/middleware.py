"""Middleware setup for the FastAPI application."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

logger = logging.getLogger(__name__)


def setup_middleware(app: FastAPI, ui_url: str = "http://localhost:5173", environment: str = "development") -> None:
    """Setup middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
        ui_url: URL of the UI application for CORS (from container apps or local)
        environment: Environment name (development, production, etc.)
    """
    # Trust proxy headers for HTTPS behind Azure Container Apps
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])  # Container Apps handles host validation

    # CORS middleware - only allow configured UI URL and localhost for local development
    allowed_origins = []
    
    # Always include the configured UI URL (from container apps or env var)
    if ui_url:
        allowed_origins.append(ui_url)
        # If UI URL is HTTP, also support HTTPS version (for production)
        if ui_url.startswith("http://"):
            allowed_origins.append(ui_url.replace("http://", "https://"))
    
    # Only allow localhost origins in development/local environment
    if environment.lower() in {"development", "local", "dev"}:
        allowed_origins.extend([
            "http://localhost:3000",
            "http://localhost:5173",
        ])
    
    # Remove duplicates while preserving order
    allowed_origins = list(dict.fromkeys(allowed_origins))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    logger.info(f"CORS enabled for origins: {allowed_origins} (environment: {environment})")
