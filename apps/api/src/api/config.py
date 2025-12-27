"""Configuration management for the Agentic API."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_env_file_path() -> str:
    """Get the path to the .env file.

    Checks for ENV_FILE environment variable first, then defaults to
    .env in the API project directory (apps/api/.env).

    Returns:
        Path to the .env file
    """
    # Check if ENV_FILE environment variable is set
    env_file = os.getenv("ENV_FILE")
    if env_file:
        return env_file

    # Default to .env in the API project directory
    # This file is in apps/api/src/api/config.py
    # So we go up 3 levels to get to apps/api/
    current_file = Path(__file__)
    api_dir = current_file.parent.parent.parent
    default_env_file = api_dir / ".env"
    return str(default_env_file)


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Application
    app_name: str = "agentic-ai"
    app_version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "info"

    # API
    api_host: str = "localhost"
    api_port: int = 8000

    # Azure Cosmos DB
    azure_cosmosdb_endpoint: str | None = None
    azure_cosmosdb_key: str | None = None
    database_name: str = "agentic"

    # OpenAI
    openai_api_key: str | None = None
    openai_model: str = "gpt-4-turbo-preview"

    # Azure AI Foundry
    foundry_project_connection_string: str | None = None
    foundry_deployment_name: str = "gpt-4.1"
    foundry_endpoint: str | None = None

    # Azure Service Bus
    azure_servicebus_connection_string: str | None = None

    # UI
    ui_url: str = "http://localhost:5173"

    # Containers
    agents_container: str = "agents"
    content_container: str = "content"
    catalog_container: str = "catalog"

    model_config = SettingsConfigDict(
        env_file=_get_env_file_path(),
        case_sensitive=False,
        env_file_encoding="utf-8",
    )


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
