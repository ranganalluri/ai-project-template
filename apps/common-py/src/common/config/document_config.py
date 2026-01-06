"""Configuration management for document processing."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class DocumentConfig(BaseSettings):
    """Application settings for document processing from environment variables."""

    # Azure Blob Storage
    azure_storage_connection_string: str | None = None
    blob_account_url: str | None = None

    # Cosmos DB
    cosmos_endpoint: str | None = None
    cosmos_key: str | None = None
    cosmos_db: str = "agenticdb"
    cosmos_container: str = "documentMetadata"

    # Content Understanding
    cu_endpoint: str | None = None
    cu_key: str | None = None

    # OpenAI (via Azure AI Foundry)
    foundry_endpoint: str | None = None
    foundry_deployment_name: str = "gpt-4.1"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_file_encoding="utf-8",
        env_prefix="",
    )


def get_document_config() -> DocumentConfig:
    """Get document processing configuration.

    Returns:
        DocumentConfig instance
    """
    return DocumentConfig()

