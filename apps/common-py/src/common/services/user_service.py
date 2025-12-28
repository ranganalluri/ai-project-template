"""User service with Cosmos DB implementation."""

import logging
from abc import ABC, abstractmethod

from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential

from common.models.user import User

logger = logging.getLogger(__name__)


class UserService(ABC):
    """Abstract interface for user service."""

    @abstractmethod
    def add_user(self, user: User) -> bool:
        """Add a user."""
        pass

    @abstractmethod
    def get_user(self, user_id: str) -> User | None:
        """Get a user by ID."""
        pass

    @abstractmethod
    def list_users(self) -> list[User]:
        """List all users."""
        pass

    @abstractmethod
    def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        pass


class CosmosUserService(UserService):
    """Cosmos DB implementation of UserService."""

    def __init__(
        self,
        cosmos_endpoint: str,
        cosmos_key: str | None = None,
        database_name: str = "agentic",
        container_name: str = "users",
        use_managed_identity: bool = False,
    ) -> None:
        """Initialize Cosmos DB user service.

        Args:
            cosmos_endpoint: Cosmos DB endpoint URL
            cosmos_key: Cosmos DB key (if not using managed identity)
            database_name: Database name
            container_name: Container name for users
            use_managed_identity: Use managed identity for authentication
        """
        
        if use_managed_identity:
            credential = DefaultAzureCredential()
            self.client = CosmosClient(cosmos_endpoint, credential)
        else:
            if not cosmos_key:
                raise ValueError("cosmos_key is required when not using managed identity")
            self.client = CosmosClient(cosmos_endpoint, cosmos_key)

        self.database = self.client.get_database_client(database_name)
        self.container = self.database.get_container_client(container_name)

    def add_user(self, user: User) -> bool:
        """Add a user."""
        try:
            user_doc = {
                "id": user.user_id,
                "user_id": user.user_id,
                **user.model_dump(),
            }
            self.container.create_item(
                body=user_doc,
                enable_automatic_id_generation=False,
            )
            return True
        except CosmosAccessConditionFailedError:
            # User already exists
            return False

    def get_user(self, user_id: str) -> User | None:
        """Get a user by ID."""
        try:
            user_doc = self.container.read_item(item=user_id, partition_key=user_id)
            return User(
                user_id=user_doc["user_id"],
                name=user_doc["name"],
                email=user_doc["email"],
            )
        except CosmosResourceNotFoundError:
            return None

    def list_users(self) -> list[User]:
        """List all users."""
        query = "SELECT * FROM c"
        items = list(self.container.query_items(query=query, enable_cross_partition_query=True))
        return [User(**item) for item in items]

    def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        try:
            self.container.delete_item(item=user_id, partition_key=user_id)
            return True
        except CosmosResourceNotFoundError:
            return False
