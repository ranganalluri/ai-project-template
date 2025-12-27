"""Service initialization and dependency injection."""

import logging

from api.config import Settings, get_settings
from common.services.chat_store import CosmosChatStore
from common.services.file_storage import BlobFileStorage
from common.services.user_service import CosmosUserService
from fastapi import Depends

logger = logging.getLogger(__name__)

# Global service instances (initialized on first use)
_chat_store: CosmosChatStore | None = None
_user_service: CosmosUserService | None = None
_file_storage: BlobFileStorage | None = None


def get_chat_store(settings: Settings = Depends(get_settings)) -> CosmosChatStore:
    """Get Cosmos DB chat store instance.

    Args:
        settings: Application settings

    Returns:
        CosmosChatStore instance
    """
    global _chat_store

    if _chat_store is None:
        if not settings.azure_cosmosdb_endpoint:
            raise ValueError("AZURE_COSMOSDB_ENDPOINT is required")

        use_managed_identity = settings.azure_cosmosdb_key is None

        _chat_store = CosmosChatStore(
            cosmos_endpoint=settings.azure_cosmosdb_endpoint,
            cosmos_key=settings.azure_cosmosdb_key,
            database_name=settings.database_name,
            runs_container_name=settings.cosmos_runs_container,
            files_container_name=settings.cosmos_files_container,
            use_managed_identity=use_managed_identity,
        )
        logger.info("Initialized CosmosChatStore")

    return _chat_store


def get_user_service(settings: Settings = Depends(get_settings)) -> CosmosUserService:
    """Get Cosmos DB user service instance.

    Args:
        settings: Application settings

    Returns:
        CosmosUserService instance
    """
    global _user_service

    if _user_service is None:
        if not settings.azure_cosmosdb_endpoint:
            raise ValueError("AZURE_COSMOSDB_ENDPOINT is required")

        use_managed_identity = settings.azure_cosmosdb_key is None

        _user_service = CosmosUserService(
            cosmos_endpoint=settings.azure_cosmosdb_endpoint,
            cosmos_key=settings.azure_cosmosdb_key,
            database_name=settings.database_name,
            container_name=settings.cosmos_users_container,
            use_managed_identity=use_managed_identity,
        )
        logger.info("Initialized CosmosUserService")

    return _user_service


def get_file_storage(settings: Settings = Depends(get_settings)) -> BlobFileStorage:
    """Get Blob Storage file service instance.

    Args:
        settings: Application settings

    Returns:
        BlobFileStorage instance
    """
    global _file_storage

    if _file_storage is None:
        if not settings.azure_storage_account_name:
            raise ValueError("AZURE_STORAGE_ACCOUNT_NAME is required")

        use_managed_identity = settings.azure_storage_account_key is None

        _file_storage = BlobFileStorage(
            account_name=settings.azure_storage_account_name,
            account_key=settings.azure_storage_account_key,
            container_name=settings.azure_storage_container_name,
            use_managed_identity=use_managed_identity,
        )
        logger.info("Initialized BlobFileStorage")

    return _file_storage
