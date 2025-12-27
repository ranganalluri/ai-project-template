"""Middleware setup for the FastAPI application."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

logger = logging.getLogger(__name__)


def setup_middleware(app: FastAPI, ui_url: str = "http://localhost:5173") -> None:
    """Setup middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
        ui_url: URL of the UI application for CORS
    """
    # Trust proxy headers for HTTPS behind Azure Container Apps
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])  # Container Apps handles host validation

    # CORS middleware - support both HTTP (local) and HTTPS (production)
    allowed_origins = [
        ui_url,
        ui_url.replace("http://", "https://"),  # Support HTTPS version
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger.info(f"CORS enabled for {allowed_origins}")
