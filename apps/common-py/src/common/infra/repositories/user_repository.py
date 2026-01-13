"""User repository for Cosmos DB data access."""

import logging

from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential

from common.models.user import User

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User]):
    """Repository for user data access with Cosmos DB.

    Responsibilities:
    - Direct Cosmos DB operations (CRUD)
    - Connection management
    - Database-level error handling
    - Map between Cosmos documents and User domain models
    - Returns User domain models (not dicts)
    """

    def __init__(
        self,
        cosmos_endpoint: str,
        cosmos_key: str | None = None,
        database_name: str = "agentic",
        container_name: str = "users",
        use_managed_identity: bool = False,
    ) -> None:
        """Initialize Cosmos DB repository.

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
                raise ValueError(
                    "cosmos_key is required when not using managed identity"
                )
            self.client = CosmosClient(cosmos_endpoint, cosmos_key)

        self.database = self.client.get_database_client(database_name)
        self.container = self.database.get_container_client(container_name)

    def _to_document(self, user: User) -> dict:
        """Convert User model to Cosmos DB document.

        Args:
            user: User domain model

        Returns:
            Cosmos DB document dict
        """
        return {
            "id": user.user_id,
            "user_id": user.user_id,
            **user.model_dump(),
        }

    def _from_document(self, doc: dict) -> User:
        """Convert Cosmos DB document to User model.

        Args:
            doc: Cosmos DB document dict

        Returns:
            User domain model
        """
        return User(
            user_id=doc["user_id"],
            first_name=doc.get("first_name", ""),
            last_name=doc.get("last_name", ""),
            email_address=doc.get("email_address", doc.get("email")),
            phone_number=doc.get("phone_number"),
        )

    def create(self, user: User) -> User:
        """Create a new user.

        Args:
            user: User domain model to create

        Returns:
            Created User domain model

        Raises:
            CosmosAccessConditionFailedError: If user already exists
        """
        logger.info("Creating user: %s", user.user_id)
        user_doc = self._to_document(user)
        created_doc = self.container.create_item(
            body=user_doc,
            enable_automatic_id_generation=False,
        )
        return self._from_document(created_doc)

    def get_by_id(self, user_id: str) -> User | None:
        """Get user by ID.

        Args:
            user_id: User ID to retrieve

        Returns:
            User domain model or None if not found
        """
        try:
            logger.debug("Fetching user: %s", user_id)
            doc = self.container.read_item(item=user_id, partition_key=user_id)
            return self._from_document(doc)
        except CosmosResourceNotFoundError:
            logger.warning("User not found: %s", user_id)
            return None

    def list_all(self, offset: int = 0, limit: int = 10) -> tuple[list[User], int]:
        """List all users with pagination.

        Args:
            offset: Number of items to skip
            limit: Maximum number of items to return

        Returns:
            Tuple of (list of User domain models, total count)
        """
        logger.debug("Listing users: offset=%s, limit=%s", offset, limit)

        # Get total count
        count_query = "SELECT VALUE COUNT(1) FROM c"
        count_result = list(
            self.container.query_items(
                query=count_query, enable_cross_partition_query=True
            )
        )
        total = count_result[0] if count_result else 0

        # Get paginated results
        sql_query = f"SELECT * FROM c OFFSET {offset} LIMIT {limit}"
        items = list(
            self.container.query_items(
                query=sql_query, enable_cross_partition_query=True
            )
        )

        users = [self._from_document(doc) for doc in items]
        return users, total

    def update(self, user_id: str, user: User) -> User | None:
        """Update an existing user.

        Args:
            user_id: User ID to update
            user: Updated User domain model

        Returns:
            Updated User domain model or None if not found
        """
        try:
            logger.info("Updating user: %s", user_id)
            user_doc = self._to_document(user)
            updated_doc = self.container.replace_item(item=user_id, body=user_doc)
            return self._from_document(updated_doc)
        except CosmosResourceNotFoundError:
            logger.warning("User not found for update: %s", user_id)
            return None

    def delete(self, user_id: str) -> bool:
        """Delete a user.

        Args:
            user_id: User ID to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            logger.info("Deleting user: %s", user_id)
            self.container.delete_item(item=user_id, partition_key=user_id)
            return True
        except CosmosResourceNotFoundError:
            logger.warning("User not found for deletion: %s", user_id)
            return False

    def search_by_name(
        self, search_term: str, offset: int = 0, limit: int = 10
    ) -> tuple[list[User], int]:
        """Search users by name.

        Args:
            search_term: Name to search for
            offset: Number of items to skip
            limit: Maximum number of items to return

        Returns:
            Tuple of (list of matching User domain models, total count)
        """
        if not search_term or not search_term.strip():
            return [], 0

        search_term_clean = search_term.strip()
        logger.debug("Searching users by name: %s", search_term_clean)

        # Cosmos DB CONTAINS query across first/last names
        sql_query = (
            "SELECT * FROM c WHERE CONTAINS(c.first_name, @term) "
            "OR CONTAINS(c.last_name, @term)"
        )
        parameters = [{"name": "@term", "value": search_term_clean}]

        try:
            items = list(
                self.container.query_items(
                    query=sql_query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )

            # Case-insensitive filtering in Python
            search_term_lower = search_term_clean.lower()
            filtered_items = []
            for item in items:
                first = item.get("first_name", "")
                last = item.get("last_name", "")
                full = f"{first} {last}".strip()
                if (
                    search_term_lower in first.lower()
                    or search_term_lower in last.lower()
                    or search_term_lower in full.lower()
                ):
                    filtered_items.append(item)

            total = len(filtered_items)
            paginated_items = filtered_items[offset : offset + limit]

            users = [self._from_document(doc) for doc in paginated_items]
            return users, total
        except Exception as e:
            logger.error("Error searching users: %s", e, exc_info=True)
            return [], 0
