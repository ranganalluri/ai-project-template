"""Dependencies for the FastAPI application."""

from api.config import get_settings
from common.infra.repositories import UserRepository
from common.use_cases.user.commands.create_user_handler import CreateUserHandler
from common.use_cases.user.commands.delete_user_handler import DeleteUserHandler
from common.use_cases.user.commands.update_user_handler import UpdateUserHandler
from common.use_cases.user.queries.get_user_handler import GetUserHandler
from common.use_cases.user.queries.get_users_handler import GetUsersHandler
from common.use_cases.user.queries.search_users_handler import SearchUsersHandler


def get_user_repository() -> UserRepository:
    """Get user repository instance.
    
    Returns:
        UserRepository instance configured with Cosmos DB settings
    """
    settings = get_settings()
    return UserRepository(
        cosmos_endpoint=settings.azure_cosmosdb_endpoint,
        cosmos_key=settings.azure_cosmosdb_key,
        database_name=settings.database_name,
        container_name="users",
        use_managed_identity=False,
    )


def get_create_user_handler() -> CreateUserHandler:
    """Get CreateUserHandler instance."""
    repository = get_user_repository()
    return CreateUserHandler(repository=repository)


def get_get_user_handler() -> GetUserHandler:
    """Get GetUserHandler instance."""
    repository = get_user_repository()
    return GetUserHandler(repository=repository)


def get_get_users_handler() -> GetUsersHandler:
    """Get GetUsersHandler instance."""
    repository = get_user_repository()
    return GetUsersHandler(repository=repository)


def get_update_user_handler() -> UpdateUserHandler:
    """Get UpdateUserHandler instance."""
    repository = get_user_repository()
    return UpdateUserHandler(repository=repository)


def get_delete_user_handler() -> DeleteUserHandler:
    """Get DeleteUserHandler instance."""
    repository = get_user_repository()
    return DeleteUserHandler(repository=repository)


def get_search_users_handler() -> SearchUsersHandler:
    """Get SearchUsersHandler instance."""
    repository = get_user_repository()
    return SearchUsersHandler(repository=repository)


__all__ = [
    "get_settings",
    "get_user_repository",
    "get_create_user_handler",
    "get_get_user_handler",
    "get_get_users_handler",
    "get_update_user_handler",
    "get_delete_user_handler",
    "get_search_users_handler",
]
