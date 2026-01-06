"""Service layer: Business logic for document metadata operations."""

import logging
from datetime import UTC, datetime

from common.infra.cosmos.cosmos_metadata_client import CosmosMetadataClient
from common.models.document import DocumentMetadata

logger = logging.getLogger(__name__)


class CosmosMetadataStore:
    """Service layer: Business logic for document metadata operations."""

    def __init__(self, client: CosmosMetadataClient | None = None) -> None:
        """Initialize metadata store.

        Args:
            client: Cosmos metadata client. If None, creates a new one.
        """
        self.client = client or CosmosMetadataClient()

    def create_metadata(self, meta: DocumentMetadata) -> DocumentMetadata:
        """Create metadata record.

        Args:
            meta: Document metadata to create

        Returns:
            Created metadata
        """
        try:
            partition_key = self.client._get_partition_key(meta.tenantId)
            created = self.client.create_item(item=meta, partition_key=partition_key)
            logger.info(f"Created metadata for document {meta.id}")
            return created
        except Exception as e:
            logger.error(f"Failed to create metadata for document {meta.id}: {e}")
            raise

    def update_metadata(self, document_id: str, tenant_id: str, patch: dict) -> DocumentMetadata:
        """Update metadata record.

        Args:
            document_id: Document ID
            tenant_id: Tenant ID
            patch: Dictionary of fields to update

        Returns:
            Updated metadata
        """
        try:
            partition_key = self.client._get_partition_key(tenant_id)
            # Add updatedAt timestamp
            patch["updatedAt"] = datetime.now(UTC)
            updated = self.client.update_item(item_id=document_id, partition_key=partition_key, updates=patch)
            logger.info(f"Updated metadata for document {document_id}")
            # Convert dict to DocumentMetadata
            return DocumentMetadata.model_validate(updated)
        except Exception as e:
            logger.error(f"Failed to update metadata for document {document_id}: {e}")
            raise

    def get_metadata(self, document_id: str, tenant_id: str) -> DocumentMetadata | None:
        """Get metadata record.

        Args:
            document_id: Document ID
            tenant_id: Tenant ID

        Returns:
            Metadata if found, None otherwise
        """
        try:
            partition_key = self.client._get_partition_key(tenant_id)
            item = self.client.read_item(item_id=document_id, partition_key=partition_key)
            if item is None:
                return None
            return DocumentMetadata.model_validate(item)
        except Exception as e:
            logger.error(f"Failed to get metadata for document {document_id}: {e}")
            raise

