"""Cosmos DB initialization service."""

import logging

from api.config import Settings
from azure.cosmos import CosmosClient, PartitionKey, exceptions

logger = logging.getLogger(__name__)


class CosmosDbInitializer:
    """Initialize Cosmos DB database and containers if they don't exist."""

    def __init__(self, settings: Settings):
        """Initialize the Cosmos DB client.

        Args:
            settings: Application settings with Cosmos DB configuration
        """
        self.settings = settings
        self.client: CosmosClient | None = None
        self.database = None

    def connect(self) -> None:
        """Create connection to Cosmos DB."""
        if not self.settings.azure_cosmosdb_endpoint or not self.settings.azure_cosmosdb_key:
            logger.warning("Cosmos DB credentials not configured. Skipping initialization.")
            return

        try:
            self.client = CosmosClient(
                url=self.settings.azure_cosmosdb_endpoint,
                credential=self.settings.azure_cosmosdb_key,
            )
            logger.info("Connected to Cosmos DB at %s", self.settings.azure_cosmosdb_endpoint)
        except Exception as e:
            logger.error("Failed to connect to Cosmos DB: %s", e)
            raise

    def initialize_database(self) -> None:
        """Create database if it doesn't exist."""
        if not self.client:
            return

        try:
            self.database = self.client.create_database_if_not_exists(id=self.settings.database_name)
            logger.info("Database '%s' initialized", self.settings.database_name)
        except Exception as e:
            logger.error("Failed to initialize database: %s", e)
            raise

    def initialize_containers(self) -> None:
        """Create containers if they don't exist."""
        if not self.database:
            return

        # Emulator typically requires provisioned throughput; use 400 only for localhost
        is_emulator = (
            bool(self.settings.azure_cosmosdb_endpoint) and "localhost" in self.settings.azure_cosmosdb_endpoint.lower()
        )

        # Create agentStore container with proper indexing policy
        # Note: Indexing policy is configured in Bicep template for production
        # This initialization is mainly for local development/emulator
        try:
            pk = PartitionKey(path="/pk")

            if is_emulator:
                self.database.create_container_if_not_exists(
                    id=self.settings.cosmos_agent_store_container,
                    partition_key=pk,
                    offer_throughput=400,
                )
            else:
                self.database.create_container_if_not_exists(
                    id=self.settings.cosmos_agent_store_container,
                    partition_key=pk,
                )

            logger.info(
                "Container '%s' initialized with partition key '/pk'",
                self.settings.cosmos_agent_store_container,
            )
        except exceptions.CosmosResourceExistsError:
            logger.info("Container '%s' already exists", self.settings.cosmos_agent_store_container)
        except Exception as e:
            logger.error(
                "Failed to create container '%s': %s",
                self.settings.cosmos_agent_store_container,
                e,
            )
            raise

        # Create users container
        try:
            user_pk = PartitionKey(path="/user_id")

            if is_emulator:
                self.database.create_container_if_not_exists(
                    id=self.settings.cosmos_users_container,
                    partition_key=user_pk,
                    offer_throughput=400,
                )
            else:
                self.database.create_container_if_not_exists(
                    id=self.settings.cosmos_users_container,
                    partition_key=user_pk,
                )

            logger.info(
                "Container '%s' initialized with partition key '/user_id'",
                self.settings.cosmos_users_container,
            )
        except exceptions.CosmosResourceExistsError:
            logger.info("Container '%s' already exists", self.settings.cosmos_users_container)
        except Exception as e:
            logger.error(
                "Failed to create container '%s': %s",
                self.settings.cosmos_users_container,
                e,
            )
            raise

    def initialize(self) -> None:
        """Run full initialization: connect, create database and containers."""
        self.connect()
        self.initialize_database()
        self.initialize_containers()
        logger.info("Cosmos DB initialization completed successfully")


async def initialize_cosmos_db(settings: Settings) -> None:
    """Initialize Cosmos DB during application startup.

    Args:
        settings: Application settings
    """
    initializer = CosmosDbInitializer(settings)
    try:
        initializer.initialize()
    except Exception as e:
        logger.error("Failed to initialize Cosmos DB: %s", e)
        if settings.environment == "production":
            raise
        # In development, log warning but allow app to continue
        logger.warning("Continuing without Cosmos DB initialization (development mode)")
