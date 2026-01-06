"""OpenAI client wrapper for Responses API using Azure AI Foundry."""

import logging

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from openai import OpenAI

from common.config.document_config import DocumentConfig

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Infrastructure layer: OpenAI client wrapper for Responses API using Azure AI Foundry."""

    def __init__(self, config: DocumentConfig | None = None) -> None:
        """Initialize OpenAI client.

        Args:
            config: Document configuration. If None, will load from environment.
        """
        if config is None:
            from common.config.document_config import get_document_config

            config = get_document_config()

        self.config = config
        self._client: OpenAI | None = None
        self._project_client: AIProjectClient | None = None

        if not config.foundry_endpoint:
            raise ValueError("FOUNDRY_ENDPOINT is required")

    def _get_project_client(self) -> AIProjectClient:
        """Get or create AI Project client.

        Returns:
            AIProjectClient instance
        """
        if self._project_client is None:
            try:
                credential = DefaultAzureCredential()
                logger.info(f"Initializing AI Project client with endpoint: {self.config.foundry_endpoint}")
                self._project_client = AIProjectClient(
                    endpoint=self.config.foundry_endpoint, credential=credential
                )
                logger.info("AI Project client initialized with managed identity")
            except Exception as e:
                logger.error(f"Failed to initialize AI Project client: {e}")
                logger.error(f"Endpoint: {self.config.foundry_endpoint}")
                logger.error(
                    "Ensure the managed identity has 'Cognitive Services User' role (not 'Cognitive Services OpenAI User')"
                )
                raise

        return self._project_client

    def get_client(self) -> OpenAI:
        """Get authenticated OpenAI client from Foundry project.

        Returns:
            OpenAI client instance
        """
        if self._client is None:
            project_client = self._get_project_client()
            self._client = project_client.get_openai_client()
            logger.info("OpenAI client initialized from Foundry project")

        return self._client

