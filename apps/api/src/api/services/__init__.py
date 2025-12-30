"""Service initialization and dependency injection."""

import logging

from api.config import Settings, get_settings
from api.services.tool_registry import ToolRegistry
from common.services.chat_store import CosmosChatStore
from common.services.file_storage import BlobFileStorage
from common.services.user_service import CosmosUserService
from fastapi import Depends

logger = logging.getLogger(__name__)

# Service instances cache
_services_cache = {}


def get_chat_store(settings: Settings = Depends(get_settings)) -> CosmosChatStore:
    """Get Cosmos DB chat store instance.

    Args:
        settings: Application settings

    Returns:
        CosmosChatStore instance
    """
    if "chat_store" not in _services_cache:
        if not settings.azure_cosmosdb_endpoint:
            raise ValueError("AZURE_COSMOSDB_ENDPOINT is required")

        use_managed_identity = settings.azure_cosmosdb_key is None

        _services_cache["chat_store"] = CosmosChatStore(
            cosmos_endpoint=settings.azure_cosmosdb_endpoint,
            cosmos_key=settings.azure_cosmosdb_key,
            database_name=settings.database_name,
            agent_store_container_name=settings.cosmos_agent_store_container,
            default_tenant_id=settings.default_tenant_id,
            use_managed_identity=use_managed_identity,
        )
        logger.info("Initialized CosmosChatStore")

    return _services_cache["chat_store"]


def get_user_service(settings: Settings = Depends(get_settings)) -> CosmosUserService:
    """Get Cosmos DB user service instance.

    Args:
        settings: Application settings

    Returns:
        CosmosUserService instance
    """
    if "user_service" not in _services_cache:
        if not settings.azure_cosmosdb_endpoint:
            raise ValueError("AZURE_COSMOSDB_ENDPOINT is required")

        use_managed_identity = settings.azure_cosmosdb_key is None

        _services_cache["user_service"] = CosmosUserService(
            cosmos_endpoint=settings.azure_cosmosdb_endpoint,
            cosmos_key=settings.azure_cosmosdb_key,
            database_name=settings.database_name,
            container_name=settings.cosmos_users_container,
            use_managed_identity=use_managed_identity,
        )
        logger.info("Initialized CosmosUserService")

    return _services_cache["user_service"]


def get_file_storage(settings: Settings = Depends(get_settings)) -> BlobFileStorage:
    """Get Blob Storage file service instance.

    Args:
        settings: Application settings

    Returns:
        BlobFileStorage instance
    """
    if "file_storage" not in _services_cache:
        if not settings.azure_storage_account_name:
            raise ValueError("AZURE_STORAGE_ACCOUNT_NAME is required")

        use_managed_identity = settings.azure_storage_account_key is None

        _services_cache["file_storage"] = BlobFileStorage(
            account_name=settings.azure_storage_account_name,
            account_key=settings.azure_storage_account_key,
            container_name=settings.azure_storage_container_name,
            use_managed_identity=use_managed_identity,
        )
        logger.info("Initialized BlobFileStorage")

    return _services_cache["file_storage"]


def get_tool_registry(settings: Settings = Depends(get_settings)) -> ToolRegistry:
    """Get ToolRegistry instance with UserService configured.

    Args:
        settings: Application settings

    Returns:
        ToolRegistry instance with UserService
    """
    if "tool_registry" not in _services_cache:
        user_service = get_user_service(settings)
        _services_cache["tool_registry"] = ToolRegistry(user_service=user_service)
        logger.info("Initialized ToolRegistry with UserService")
    return _services_cache["tool_registry"]
