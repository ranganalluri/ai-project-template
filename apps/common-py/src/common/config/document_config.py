"""Configuration management for document processing."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

def _get_env_file_path() -> str:
    """Get the path to the .env file.

    Checks for ENV_FILE environment variable first, then defaults to
    .env in the common-py project directory (apps/common-py/.env).

    Returns:
        Path to the .env file
    """
    # Default to .env in the common-py project directory
    # This file is in apps/common-py/src/common/config/document_config.py
    # So we go up 4 levels to get to apps/common-py/
    current_file = Path(__file__)
    common_py_dir = current_file.parent.parent.parent.parent
    default_env_file = common_py_dir / ".env"
    return str(default_env_file)


class DocumentConfig(BaseSettings):
    """Application settings for document processing from environment variables."""

    # Azure Blob Storage
    azure_storage_account_name: str | None = None
    azure_storage_account_key: str | None = None
    blob_account_url: str | None = None

    # Cosmos DB
    azure_cosmosdb_endpoint: str | None = None
    azure_cosmosdb_key: str | None = None
    cosmos_db: str = "agenticdb"
    cosmos_container: str = "documentMetadata"

    # Content Understanding
    cu_endpoint: str | None = None
    cu_key: str | None = None

    # OpenAI (via Azure AI Foundry)
    foundry_endpoint: str | None = None
    foundry_deployment_name: str = "gpt-4.1"

    model_config = SettingsConfigDict(
        env_file=_get_env_file_path(),
        case_sensitive=False,
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
    )


def get_document_config() -> DocumentConfig:
    """Get document processing configuration.

    Returns:
        DocumentConfig instance
    """
    return DocumentConfig()
