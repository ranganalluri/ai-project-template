"""Cosmos DB client for document metadata."""

import logging

from common.infra.cosmos.cosmos_base import BaseCosmosClient
from common.models.document import Cu_Record

logger = logging.getLogger(__name__)


class CosmosMetadataClient(BaseCosmosClient[Cu_Record]):
    """Infrastructure layer: Cosmos DB client for document metadata."""

    def __init__(self, config=None, container_name: str | None = None) -> None:
        """Initialize Cosmos metadata client.

        Args:
            config: Document configuration. If None, will load from environment.
            container_name: Container name. If None, uses config.cosmos_container.
        """
        if config is None:
            from common.config.document_config import get_document_config

            config = get_document_config()

        container = container_name or config.cosmos_container
        super().__init__(
            container_name=container,
            partition_key_path="/id",
            config=config,
        )

    def _get_partition_key(self, document_id: str) -> str:
        """Get partition key for metadata document.

        Args:
            document_id: Document ID (used as partition key)

        Returns:
            Partition key value (document ID)
        """
        return document_id

