"""Handler for CreateUserCommand - saves users to Cosmos DB."""

import logging
from uuid import uuid4

from azure.cosmos.exceptions import CosmosAccessConditionFailedError

from common.use_cases.user.commands.create_user import CreateUserCommand
from common.infra.repositories import UserRepository
from common.models.user import User
from common.use_cases.user.queries import UserResponse

logger = logging.getLogger(__name__)


class CreateUserHandler:
    """Handler for creating and saving new users to Cosmos DB.
    
    Responsibilities:
    - Accept and validate CreateUserCommand
    - Map command to User domain model (handler does mapping)
    - Generate unique user_id
    - Call repository to save user
    - Handle duplicate user errors (email already exists)
    - Map User model to UserResponse DTO
    """

    def __init__(self, repository: UserRepository):
        """Initialize handler with repository.
        
        Args:
            repository: UserRepository for data access
        """
        self.repository = repository

    def handle(self, command: CreateUserCommand) -> UserResponse:
        """Create and save a new user to Cosmos DB.
        
        Flow:
        1. Validate command (Pydantic handles this automatically)
        2. Map CreateUserCommand → User domain model (handler responsibility)
        3. Convert User → Cosmos DB document (handler responsibility)
        4. Call repository to save document
        5. Map saved document → UserResponse (handler responsibility)
        
        Args:
            command: CreateUserCommand DTO with user data
                - first_name: str (required)
                - last_name: str (required)
                - email_address: EmailStr (required, unique)
                - phone_number: str | None (optional)
            
        Returns:
            UserResponse DTO with created user
                
        Raises:
            ValueError: If user with same email already exists
            Exception: For other Cosmos DB errors
            
        Example:
            >>> from common.use_cases.user.commands import CreateUserHandler, CreateUserCommand
            >>> from common.infra.repositories import UserRepository
            >>>
            >>> repository = UserRepository(endpoint, key)
            >>> handler = CreateUserHandler(repository)
            >>> command = CreateUserCommand(first_name="Jane", last_name="Doe", email_address="jane.doe@example.com", phone_number="+1234567890")
            >>> response = handler.handle(command)
            >>> print(f"Created user: {response.user_id}")
        """
        try:
            logger.info("CreateUserHandler: Creating user with email %s", command.email_address)
            
            # Map command to domain model (handler responsibility)
            user = User(
                user_id=f"user-{uuid4()}",
                first_name=command.first_name,
                last_name=command.last_name,
                email_address=command.email_address,
                phone_number=command.phone_number,
            )
            logger.debug("CreateUserHandler: Mapped to User model with id %s", user.user_id)
            
            # Save via repository (repository handles document conversion)
            created_user = self.repository.create(user)
            logger.info("CreateUserHandler: User saved successfully: %s", created_user.user_id)
            
            # Map to response DTO (handler responsibility)
            response = UserResponse(
                user_id=created_user.user_id,
                first_name=created_user.first_name,
                last_name=created_user.last_name,
                email_address=created_user.email_address,
                phone_number=created_user.phone_number,
                account_status="active",
            )
            logger.debug("CreateUserHandler: Mapped to UserResponse")
            
            return response
            
        except CosmosAccessConditionFailedError as e:
            logger.warning(
                "CreateUserHandler: Duplicate user - email already exists: %s",
                command.email_address
            )
            raise ValueError(f"User with email {command.email_address} already exists") from e
        except Exception as e:
            logger.error(
                "CreateUserHandler: Failed to create user - %s: %s",
                type(e).__name__, e
            )
            raise
