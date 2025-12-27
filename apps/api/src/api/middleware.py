"""Middleware setup for the FastAPI application."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


def get_allowed_origins(ui_url: str | None = None, environment: str = "development") -> list[str]:
    """Get list of allowed CORS origins based on configuration.

    Args:
        ui_url: URL of the UI application (from container apps or env var)
        environment: Environment name (development, production, etc.)

    Returns:
        List of allowed origin URLs
    """
    allowed_origins: list[str] = []

    # Add configured UI URL (if provided)
    if ui_url:
        allowed_origins.append(ui_url.rstrip("/"))
        if ui_url.startswith("http://"):
            allowed_origins.append(ui_url.replace("http://", "https://", 1).rstrip("/"))
        if ui_url.startswith("https://"):
            allowed_origins.append(ui_url.replace("https://", "http://", 1).rstrip("/"))

    # Dev/local origins (Vite commonly uses both)
    if environment.lower() in {"development", "dev", "local"}:
        allowed_origins.extend(
            [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ]
        )

    # Deduplicate while preserving order
    return list(dict.fromkeys(allowed_origins))


def get_cors_headers(origin: str | None, ui_url: str | None = None, environment: str = "development") -> dict[str, str]:
    """Get CORS headers for a given origin.

    Args:
        origin: The origin from the request header
        ui_url: URL of the UI application (from container apps or env var)
        environment: Environment name (development, production, etc.)

    Returns:
        Dictionary of CORS headers, empty if origin is not allowed
    """
    if not origin:
        return {}

    allowed_origins = get_allowed_origins(ui_url, environment)

    # Check if origin is allowed
    if origin in allowed_origins:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    return {}


def setup_middleware(app: FastAPI, ui_url: str | None = None, environment: str = "development") -> None:
    """Setup middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
        ui_url: URL of the UI application for CORS (from container apps or local)
        environment: Environment name (development, production, etc.)
    """
    allowed_origins = get_allowed_origins(ui_url, environment)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    logger.info("CORS enabled for origins: %s (environment=%s)", allowed_origins, environment)
