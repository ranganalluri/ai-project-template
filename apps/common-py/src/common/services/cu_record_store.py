"""Service layer: Business logic for document metadata operations."""

import logging
from datetime import UTC, datetime

from common.infra.cosmos.cosmos_metadata_client import CosmosMetadataClient
from common.models.document import Cu_Record

logger = logging.getLogger(__name__)


class CuRecordStore:
    """Service layer: Business logic for document metadata operations."""

    def __init__(self, client: CosmosMetadataClient | None = None) -> None:
        """Initialize metadata store.

        Args:
            client: Cosmos metadata client. If None, creates a new one.
        """
        self.client = client or CosmosMetadataClient()

    def create_metadata(self, meta: Cu_Record) -> Cu_Record:
        """Create metadata record.

        Args:
            meta: Document metadata to create

        Returns:
            Created metadata
        """
        try:
            # Use document ID as partition key
            partition_key = self.client._get_partition_key(meta.id)
            created_dict = self.client.create_item(item=meta, partition_key=partition_key)
            logger.info("Created metadata for document %s", meta.id)
            # Validate the returned dictionary as Cu_Record
            return Cu_Record.model_validate(created_dict)
        except Exception as e:
            logger.error("Failed to create metadata for document %s: %s", meta.id, e)
            raise

    def update_metadata(self, document_id: str, tenant_id: str, patch: dict) -> Cu_Record:
        """Update metadata record.

        Args:
            document_id: Document ID (used as partition key)
            tenant_id: Tenant ID (kept for backward compatibility, not used for partition key)
            patch: Dictionary of fields to update

        Returns:
            Updated metadata
        """
        try:
            # Use document ID as partition key
            partition_key = self.client._get_partition_key(document_id)
            # Add updatedAt timestamp
            patch["updatedAt"] = datetime.now(UTC)
            updated = self.client.update_item(item_id=document_id, partition_key=partition_key, updates=patch)
            logger.info("Updated metadata for document %s", document_id)
            # Convert dict to DocumentMetadata
            return Cu_Record.model_validate(updated)
        except Exception as e:
            logger.error("Failed to update metadata for document %s: %s", document_id, e)
            raise

    def get_metadata(self, document_id: str, tenant_id: str) -> Cu_Record | None:
        """Get metadata record.

        Args:
            document_id: Document ID (used as partition key)
            tenant_id: Tenant ID (kept for backward compatibility, not used for partition key)

        Returns:
            Metadata if found, None otherwise
        """
        try:
            # Use document ID as partition key
            partition_key = self.client._get_partition_key(document_id)
            item = self.client.read_item(item_id=document_id, partition_key=partition_key)
            if item is None:
                return None
            # Ensure required fields are present and handle missing optional fields
            # Cosmos DB stores data with aliases (camelCase), but Pydantic can handle both
            # with populate_by_name=True
            if "id" not in item:
                item["id"] = document_id
            # Validate with populate_by_name to handle both Python names and aliases
            return Cu_Record.model_validate(item, strict=False)
        except Exception as e:
            logger.error("Failed to get metadata for document %s: %s", document_id, e)
            raise

