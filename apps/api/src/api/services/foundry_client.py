"""Azure AI Foundry client service."""

import logging

from api.config import Settings
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from openai import OpenAI

logger = logging.getLogger(__name__)


class FoundryClient:
    """Client for Azure AI Foundry integration."""

    def __init__(self, settings: Settings) -> None:
        """Initialize Foundry client.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self._client: OpenAI | None = None
        self._project_client: AIProjectClient | None = None

    def _get_project_client(self) -> AIProjectClient:
        """Get or create AI Project client.

        Returns:
            AIProjectClient instance
        """
        if self._project_client is None:
            if not self.settings.foundry_endpoint:
                raise ValueError("FOUNDRY_ENDPOINT is not set")

            try:
                credential = DefaultAzureCredential()
                logger.info(f"Initializing AI Project client with endpoint: {self.settings.foundry_endpoint}")
                self._project_client = AIProjectClient(endpoint=self.settings.foundry_endpoint, credential=credential)
                logger.info("AI Project client initialized with managed identity")
            except Exception as e:
                logger.error(f"Failed to initialize AI Project client: {e}")
                logger.error(f"Endpoint: {self.settings.foundry_endpoint}")
                logger.error(
                    "Ensure the managed identity has 'Cognitive Services User' role (not 'Cognitive Services OpenAI User')"
                )
                raise

        return self._project_client

    def get_openai_client(self) -> OpenAI:
        """Get authenticated OpenAI client from Foundry project.

        Returns:
            OpenAI client instance
        """
        if self._client is None:
            project_client = self._get_project_client()
            self._client = project_client.get_openai_client()
            logger.info("OpenAI client initialized from Foundry project")

        return self._client

    def is_configured(self) -> bool:
        """Check if Foundry is properly configured.

        Returns:
            True if configuration is present
        """
        return bool(self.settings.foundry_endpoint)
