"""Generic base class for Cosmos DB client operations."""

import logging
from typing import Generic, TypeVar

from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential
from pydantic import BaseModel

from common.config.document_config import DocumentConfig

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class BaseCosmosClient(Generic[T]):
    """Infrastructure layer: Generic base class for Cosmos DB client operations."""

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

        if not config.cosmos_endpoint:
            raise ValueError("COSMOS_ENDPOINT is required")

        # Initialize Cosmos client
        if config.cosmos_key:
            # Use key-based authentication
            self.client = CosmosClient(url=config.cosmos_endpoint, credential=config.cosmos_key)
        else:
            # Use managed identity
            credential = DefaultAzureCredential()
            self.client = CosmosClient(url=config.cosmos_endpoint, credential=credential)

        # Get database and container
        db_name = database_name or config.cosmos_db
        self.database = self.client.get_database_client(db_name)
        self.container = self.database.get_container_client(container_name)

    def create_item(self, item: T, partition_key: str) -> T:
        """Create an item in Cosmos DB.

        Args:
            item: Pydantic model instance to create
            partition_key: Partition key value

        Returns:
            Created item as Pydantic model
        """
        try:
            item_dict = item.model_dump(mode="json")
            item_dict["id"] = item_dict.get("id", item_dict.get("id"))
            created = self.container.create_item(body=item_dict)
            logger.info(f"Created item {created['id']} in container {self.container_name}")
            return item.model_validate(created)
        except CosmosAccessConditionFailedError as e:
            logger.error(f"Item already exists or conflict: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create item in {self.container_name}: {e}")
            raise

    def read_item(self, item_id: str, partition_key: str) -> T | None:
        """Read an item from Cosmos DB.

        Args:
            item_id: Item ID
            partition_key: Partition key value

        Returns:
            Item as Pydantic model, or None if not found
        """
        try:
            item = self.container.read_item(item=item_id, partition_key=partition_key)
            logger.debug(f"Read item {item_id} from container {self.container_name}")
            # Note: Type T needs to be provided by subclass
            return item  # type: ignore
        except CosmosResourceNotFoundError:
            logger.debug(f"Item {item_id} not found in container {self.container_name}")
            return None
        except Exception as e:
            logger.error(f"Failed to read item {item_id} from {self.container_name}: {e}")
            raise

    def update_item(self, item_id: str, partition_key: str, updates: dict) -> T:
        """Update an item in Cosmos DB (partial update).

        Args:
            item_id: Item ID
            partition_key: Partition key value
            updates: Dictionary of fields to update

        Returns:
            Updated item as Pydantic model
        """
        try:
            # Read existing item
            existing = self.container.read_item(item=item_id, partition_key=partition_key)
            # Merge updates
            existing.update(updates)
            # Replace item
            updated = self.container.replace_item(item=item_id, body=existing)
            logger.info(f"Updated item {item_id} in container {self.container_name}")
            return updated  # type: ignore
        except CosmosResourceNotFoundError:
            logger.error(f"Item {item_id} not found for update in {self.container_name}")
            raise
        except Exception as e:
            logger.error(f"Failed to update item {item_id} in {self.container_name}: {e}")
            raise

    def replace_item(self, item: T, partition_key: str) -> T:
        """Replace an item in Cosmos DB (full replace).

        Args:
            item: Pydantic model instance to replace
            partition_key: Partition key value

        Returns:
            Replaced item as Pydantic model
        """
        try:
            item_dict = item.model_dump(mode="json")
            item_dict["id"] = item_dict.get("id", item_dict.get("id"))
            replaced = self.container.replace_item(item=item_dict["id"], body=item_dict)
            logger.info(f"Replaced item {item_dict['id']} in container {self.container_name}")
            return item.model_validate(replaced)
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

