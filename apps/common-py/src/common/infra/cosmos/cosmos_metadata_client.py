"""Cosmos DB client for document metadata."""

import logging

from common.infra.cosmos.cosmos_base import BaseCosmosClient
from common.models.document import DocumentMetadata

logger = logging.getLogger(__name__)


class CosmosMetadataClient(BaseCosmosClient[DocumentMetadata]):
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
            partition_key_path="/tenantId",
            config=config,
        )

    def _get_partition_key(self, tenant_id: str) -> str:
        """Get partition key for metadata document.

        Args:
            tenant_id: Tenant ID

        Returns:
            Partition key value
        """
        return tenant_id

