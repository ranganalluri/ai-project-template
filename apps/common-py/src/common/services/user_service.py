"""User service with Cosmos DB implementation."""

import logging
from abc import ABC, abstractmethod

from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosAccessConditionFailedError, CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential

from common.models.user import User
from common.dtos.commands.user_commands import CreateUserCommand, UpdateUserCommand
from common.dtos.queries.user_queries import GetUserQuery, ListUsersQuery, SearchUsersQuery, UserResponse, UserListResponse
from common.utils.user_mapper import UserMapper

logger = logging.getLogger(__name__)


class UserService(ABC):
    """Abstract interface for user service."""

    @abstractmethod
    def create_user(self, command: CreateUserCommand) -> UserResponse:
        """Create a new user.

        Args:
            command: CreateUserCommand DTO

        Returns:
            UserResponse DTO
        """
        pass

    @abstractmethod
    def get_user(self, query: GetUserQuery) -> UserResponse | None:
        """Get a user by ID.

        Args:
            query: GetUserQuery DTO

        Returns:
            UserResponse DTO or None if not found
        """
        pass

    @abstractmethod
    def list_users(self, query: ListUsersQuery) -> UserListResponse:
        """List users with pagination.

        Args:
            query: ListUsersQuery DTO

        Returns:
            UserListResponse DTO with pagination
        """
        pass

    @abstractmethod
    def update_user(self, user_id: str, command: UpdateUserCommand) -> UserResponse | None:
        """Update an existing user.

        Args:
            user_id: User ID to update
            command: UpdateUserCommand DTO

        Returns:
            UserResponse DTO or None if not found
        """
        pass

    @abstractmethod
    def delete_user(self, user_id: str) -> bool:
        """Delete a user.

        Args:
            user_id: User ID to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def search_users(self, query: SearchUsersQuery) -> UserListResponse:
        """Search for users by name with pagination.

        Args:
            query: SearchUsersQuery DTO

        Returns:
            UserListResponse DTO with search results
        """
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
        self.mapper = UserMapper()

    def create_user(self, command: CreateUserCommand) -> UserResponse:
        """Create a new user.

        Args:
            command: CreateUserCommand DTO

        Returns:
            UserResponse DTO

        Raises:
            ValueError: If user already exists
        """
        try:
            user = self.mapper.from_create_command(command)
            user_doc = self.mapper.to_cosmos_document(user)
            self.container.create_item(
                body=user_doc,
                enable_automatic_id_generation=False,
            )
            return self.mapper.to_response(user)
        except CosmosAccessConditionFailedError as e:
            raise ValueError(f"User with email {command.email} already exists") from e

    def get_user(self, query: GetUserQuery) -> UserResponse | None:
        """Get a user by ID.

        Args:
            query: GetUserQuery DTO

        Returns:
            UserResponse DTO or None if not found
        """
        try:
            user_doc = self.container.read_item(item=query.user_id, partition_key=query.user_id)
            user = self.mapper.from_cosmos_document(user_doc)
            return self.mapper.to_response(user)
        except CosmosResourceNotFoundError:
            return None

    def list_users(self, query: ListUsersQuery) -> UserListResponse:
        """List users with pagination.

        Args:
            query: ListUsersQuery DTO

        Returns:
            UserListResponse DTO with pagination
        """
        # Get total count
        count_query = "SELECT VALUE COUNT(1) FROM c"
        count_result = list(self.container.query_items(query=count_query, enable_cross_partition_query=True))
        total = count_result[0] if count_result else 0

        # Get paginated results
        offset = (query.page - 1) * query.page_size
        sql_query = f"SELECT * FROM c OFFSET {offset} LIMIT {query.page_size}"
        items = list(self.container.query_items(query=sql_query, enable_cross_partition_query=True))
        
        users = [self.mapper.from_cosmos_document(item) for item in items]
        return self.mapper.to_response_list(users, total, query.page, query.page_size)

    def update_user(self, user_id: str, command: UpdateUserCommand) -> UserResponse | None:
        """Update an existing user.

        Args:
            user_id: User ID to update
            command: UpdateUserCommand DTO

        Returns:
            UserResponse DTO or None if not found
        """
        try:
            # Get existing user
            user_doc = self.container.read_item(item=user_id, partition_key=user_id)
            user = self.mapper.from_cosmos_document(user_doc)
            
            # Apply updates
            updated_user = self.mapper.apply_update_command(user, command)
            updated_doc = self.mapper.to_cosmos_document(updated_user)
            
            # Save to database
            self.container.replace_item(item=user_id, body=updated_doc)
            return self.mapper.to_response(updated_user)
        except CosmosResourceNotFoundError:
            return None

    def delete_user(self, user_id: str) -> bool:
        """Delete a user.

        Args:
            user_id: User ID to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            self.container.delete_item(item=user_id, partition_key=user_id)
            return True
        except CosmosResourceNotFoundError:
            return False

    def search_users(self, query: SearchUsersQuery) -> UserListResponse:
        """Search for users by name with pagination.

        Args:
            query: SearchUsersQuery DTO

        Returns:
            UserListResponse DTO with search results
        """
        if not query.name or not query.name.strip():
            return self.mapper.to_response_list([], 0, query.page, query.page_size)

        search_term = query.name.strip()
        
        # Cosmos DB CONTAINS is case-sensitive, so we'll do case-insensitive filtering in Python
        sql_query = "SELECT * FROM c WHERE CONTAINS(c.name, @name)"
        parameters = [{"name": "@name", "value": search_term}]

        try:
            items = list(
                self.container.query_items(
                    query=sql_query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )
            # Filter results case-insensitively in Python for true case-insensitive matching
            search_term_lower = search_term.lower()
            filtered_items = [item for item in items if search_term_lower in item.get("name", "").lower()]
            
            # Apply pagination
            total = len(filtered_items)
            offset = (query.page - 1) * query.page_size
            paginated_items = filtered_items[offset : offset + query.page_size]
            
            users = [self.mapper.from_cosmos_document(item) for item in paginated_items]
            return self.mapper.to_response_list(users, total, query.page, query.page_size)
        except Exception as e:
            logger.error("Error searching users: %s", e, exc_info=True)
            # Fallback: get all users and filter in Python (less efficient but more reliable)
            try:
                query_fallback = "SELECT * FROM c"
                all_items = list(
                    self.container.query_items(
                        query=query_fallback,
                        enable_cross_partition_query=True,
                    )
                )
                search_term_lower = search_term.lower()
                filtered_items = [item for item in all_items if search_term_lower in item.get("name", "").lower()]
                
                # Apply pagination
                total = len(filtered_items)
                offset = (query.page - 1) * query.page_size
                paginated_items = filtered_items[offset : offset + query.page_size]
                
                users = [self.mapper.from_cosmos_document(item) for item in paginated_items]
                return self.mapper.to_response_list(users, total, query.page, query.page_size)
            except Exception as e2:
                logger.error("Error in fallback search: %s", e2, exc_info=True)
                return self.mapper.to_response_list([], 0, query.page, query.page_size)
