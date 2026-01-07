"""Generic base class for Cosmos DB client operations."""

import logging
from datetime import datetime
from typing import Any

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential
from pydantic import BaseModel

from common.config.document_config import DocumentConfig

logger = logging.getLogger(__name__)


class BaseCosmosClient[T: BaseModel]:
    """Infrastructure layer: Generic base class for Cosmos DB client operations."""

    @staticmethod
    def _serialize_datetimes(obj: Any) -> Any:
        """Recursively serialize datetime objects to ISO format strings.
        
        Args:
            obj: Object that may contain datetime objects
            
        Returns:
            Object with datetime objects converted to ISO format strings
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: BaseCosmosClient._serialize_datetimes(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [BaseCosmosClient._serialize_datetimes(item) for item in obj]
        else:
            return obj

    def __init__(
        self,
        container_name: str,
        partition_key_path: str = "/id",
        config: DocumentConfig | None = None,
        database_name: str | None = None,
    ) -> None:
        """Initialize Cosmos DB client.

        Args:
            container_name: Container name
            partition_key_path: Partition key path (default: "/id")
            config: Document configuration. If None, will load from environment.
            database_name: Database name. If None, uses config.cosmos_db.
        """
        if config is None:
            from common.config.document_config import get_document_config

            config = get_document_config()

        self.config = config
        self.container_name = container_name
        self.partition_key_path = partition_key_path

        if not config.azure_cosmosdb_endpoint:
            raise ValueError("AZURE_COSMOSDB_ENDPOINT is required")

        # Initialize Cosmos client
        if config.azure_cosmosdb_key:
            # Use key-based authentication
            self.client = CosmosClient(url=config.azure_cosmosdb_endpoint, credential=config.azure_cosmosdb_key)
        else:
            # Use managed identity
            credential = DefaultAzureCredential()
            self.client = CosmosClient(url=config.azure_cosmosdb_endpoint, credential=credential)

        # Get database and container
        db_name = database_name or config.cosmos_db
        self.database = self.client.get_database_client(db_name)
        
        # Ensure container exists (create if not exists)
        self._ensure_container_exists(container_name, partition_key_path)
        
        self.container = self.database.get_container_client(container_name)

    def _ensure_container_exists(self, container_name: str, partition_key_path: str) -> None:
        """Ensure container exists, create if it doesn't.
        
        Args:
            container_name: Container name
            partition_key_path: Partition key path
        """
        try:
            # Try to read container to check if it exists
            self.database.get_container_client(container_name).read()
            logger.debug("Container '%s' already exists", container_name)
        except CosmosResourceNotFoundError:
            # Container doesn't exist, create it
            try:
                is_emulator = (
                    bool(self.config.azure_cosmosdb_endpoint) 
                    and "localhost" in self.config.azure_cosmosdb_endpoint.lower()
                )
                
                pk = PartitionKey(path=partition_key_path)

                if is_emulator:
                    self.database.create_container(
                        id=container_name,
                        partition_key=pk,
                        offer_throughput=400,
                    )
                else:
                    self.database.create_container(
                        id=container_name,
                        partition_key=pk,
                    )
                
                logger.info(
                    "Created container '%s' with partition key '%s'",
                    container_name,
                    partition_key_path,
                )
            except Exception as e:
                logger.warning(
                    "Failed to create container '%s': %s. It may already exist or you may not have permissions.",
                    container_name,
                    e,
                )
                # Don't raise - allow the app to continue, container might exist

    def create_item(self, item: T, partition_key: str) -> dict:
        """Create an item in Cosmos DB.

        Args:
            item: Pydantic model instance to create
            partition_key: Partition key value

        Returns:
            Created item as dictionary (with Cosmos system fields removed)
        """
        try:
            item_dict = item.model_dump(mode="json", by_alias=True)
            item_dict["id"] = item_dict.get("id", item_dict.get("id"))
            created = self.container.create_item(body=item_dict)
            logger.info("Created item %s in container %s", created["id"], self.container_name)
            # Remove Cosmos DB system fields
            cosmos_system_fields = {"_rid", "_self", "_etag", "_attachments", "_ts"}
            filtered_item = {k: v for k, v in created.items() if k not in cosmos_system_fields}
            return filtered_item
        except CosmosAccessConditionFailedError as e:
            logger.error(f"Item already exists or conflict: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create item in {self.container_name}: {e}")
            raise

    def read_item(self, item_id: str, partition_key: str) -> dict | None:
        """Read an item from Cosmos DB.

        Args:
            item_id: Item ID
            partition_key: Partition key value

        Returns:
            Item as dictionary (with Cosmos system fields removed), or None if not found
        """
        try:
            item = self.container.read_item(item=item_id, partition_key=partition_key)
            logger.debug("Read item %s from container %s", item_id, self.container_name)
            # Remove Cosmos DB system fields that aren't part of the model
            cosmos_system_fields = {"_rid", "_self", "_etag", "_attachments", "_ts"}
            filtered_item = {k: v for k, v in item.items() if k not in cosmos_system_fields}
            # Ensure 'id' field is present (required field)
            if "id" not in filtered_item:
                filtered_item["id"] = item_id
            return filtered_item
        except CosmosResourceNotFoundError:
            logger.debug("Item %s not found in container %s", item_id, self.container_name)
            return None
        except Exception as e:
            logger.error("Failed to read item %s from %s: %s", item_id, self.container_name, e)
            raise

    def update_item(self, item_id: str, partition_key: str, updates: dict) -> dict:
        """Update an item in Cosmos DB (partial update).

        Args:
            item_id: Item ID
            partition_key: Partition key value
            updates: Dictionary of fields to update

        Returns:
            Updated item as dictionary (with Cosmos system fields removed)
        """
        try:
            # Read existing item
            existing = self.container.read_item(item=item_id, partition_key=partition_key)
            # Serialize updates dictionary (may contain datetime objects)
            serialized_updates = self._serialize_datetimes(updates)
            # Merge updates
            existing.update(serialized_updates)
            # Serialize datetime objects in existing item to ISO format strings for JSON serialization
            serialized_item = self._serialize_datetimes(existing)
            # Replace item
            updated = self.container.replace_item(item=item_id, body=serialized_item)
            logger.info("Updated item %s in container %s", item_id, self.container_name)
            # Remove Cosmos DB system fields
            cosmos_system_fields = {"_rid", "_self", "_etag", "_attachments", "_ts"}
            filtered_item = {k: v for k, v in updated.items() if k not in cosmos_system_fields}
            return filtered_item
        except CosmosResourceNotFoundError:
            logger.error(f"Item {item_id} not found for update in {self.container_name}")
            raise
        except Exception as e:
            logger.error(f"Failed to update item {item_id} in {self.container_name}: {e}")
            raise

    def replace_item(self, item: T, partition_key: str) -> dict:
        """Replace an item in Cosmos DB (full replace).

        Args:
            item: Pydantic model instance to replace
            partition_key: Partition key value

        Returns:
            Replaced item as dictionary (with Cosmos system fields removed)
        """
        try:
            item_dict = item.model_dump(mode="json", by_alias=True)
            item_dict["id"] = item_dict.get("id", item_dict.get("id"))
            replaced = self.container.replace_item(item=item_dict["id"], body=item_dict)
            logger.info("Replaced item %s in container %s", item_dict["id"], self.container_name)
            # Remove Cosmos DB system fields
            cosmos_system_fields = {"_rid", "_self", "_etag", "_attachments", "_ts"}
            filtered_item = {k: v for k, v in replaced.items() if k not in cosmos_system_fields}
            return filtered_item
        except CosmosResourceNotFoundError:
            logger.error(f"Item {item.model_dump().get('id')} not found for replace in {self.container_name}")
            raise
        except Exception as e:
            logger.error(f"Failed to replace item in {self.container_name}: {e}")
            raise

    def query_items(self, query: str, partition_key: str | None = None) -> list[dict]:
        """Query items from Cosmos DB.

        Args:
            query: SQL query string
            partition_key: Optional partition key for cross-partition queries

        Returns:
            List of items as dictionaries
        """
        try:
            if partition_key:
                items = list(
                    self.container.query_items(
                        query=query, partition_key=partition_key, enable_cross_partition_query=False
                    )
                )
            else:
                items = list(self.container.query_items(query=query, enable_cross_partition_query=True))
            logger.debug(f"Queried {len(items)} items from container {self.container_name}")
            return items
        except Exception as e:
            logger.error(f"Failed to query items from {self.container_name}: {e}")
            raise

    def delete_item(self, item_id: str, partition_key: str) -> None:
        """Delete an item from Cosmos DB.

        Args:
            item_id: Item ID
            partition_key: Partition key value
        """
        try:
            self.container.delete_item(item=item_id, partition_key=partition_key)
            logger.info(f"Deleted item {item_id} from container {self.container_name}")
        except CosmosResourceNotFoundError:
            logger.warning(f"Item {item_id} not found for deletion in {self.container_name}")
        except Exception as e:
            logger.error(f"Failed to delete item {item_id} from {self.container_name}: {e}")
            raise

