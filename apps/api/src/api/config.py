"""Configuration management for the Agentic API."""


from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Application
    app_name: str = "agentic-ai"
    app_version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "info"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Azure Cosmos DB
    azure_cosmosdb_endpoint: str | None = None
    azure_cosmosdb_key: str | None = None
    database_name: str = "agentic"

    # OpenAI
    openai_api_key: str | None = None
    openai_model: str = "gpt-4-turbo-preview"

    # Azure Service Bus
    azure_servicebus_connection_string: str | None = None

    # UI
    ui_url: str = "http://localhost:5173"

    # Containers
    agents_container: str = "agents"
    content_container: str = "content"
    catalog_container: str = "catalog"

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
