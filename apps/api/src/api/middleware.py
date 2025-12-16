"""Middleware setup for the FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

logger = logging.getLogger(__name__)


def setup_middleware(app: FastAPI, ui_url: str = "http://localhost:5173") -> None:
    """Setup middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
        ui_url: URL of the UI application for CORS
    """
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            ui_url,
            "http://localhost:3000",  # Production UI
            "http://localhost:5173",  # Dev UI
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger.info(f"CORS enabled for {ui_url}")
