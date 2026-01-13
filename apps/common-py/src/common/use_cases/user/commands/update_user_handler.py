"""Handler for UpdateUserCommand - updates existing users."""

import logging

from common.use_cases.user.commands.update_user import UpdateUserCommand
from common.use_cases.user.queries import UserResponse
from common.models.user import User
from common.infra.repositories import UserRepository

logger = logging.getLogger(__name__)


class UpdateUserHandler:
    """Handler for updating existing users.
    
    Responsibilities:
    - Accept and validate UpdateUserCommand
    - Get existing user from repository
    - Apply updates to User model (handler responsibility)
    - Map User to Cosmos DB document (handler responsibility)
    - Call repository to save updated document
    - Map updated User to UserResponse (handler responsibility)
    """

    def __init__(self, repository: UserRepository):
        """Initialize handler with repository.
        
        Args:
            repository: UserRepository for data access
        """
        self.repository = repository

    def handle(self, user_id: str, command: UpdateUserCommand) -> UserResponse | None:
        """Update an existing user.
        
        Flow:
        1. Get existing User from repository (repository handles document conversion)
        2. Apply updates from command (handler responsibility)
        3. Call repository to save updated User (repository handles document conversion)
        4. Map saved User → UserResponse (handler responsibility)
        
        Args:
            user_id: User ID to update
            command: UpdateUserCommand with fields to update
            
        Returns:
            UserResponse DTO or None if user not found
                
        Example:
            >>> from common.use_cases.user.commands import UpdateUserHandler, UpdateUserCommand
            >>> from common.infra.repositories import UserRepository
            >>> 
            >>> repository = UserRepository(endpoint, key)
            >>> handler = UpdateUserHandler(repository)
            >>> command = UpdateUserCommand(user_id="user-123", first_name="Jane")
            >>> response = handler.handle("user-123", command)
            >>> if response:
            ...     print(f"Updated user: {response.name}")
        """
        try:
            logger.info("UpdateUserHandler: Updating user %s", user_id)
            
            # Get existing user (returns User model)
            user = self.repository.get_by_id(user_id)
            if not user:
                logger.warning("UpdateUserHandler: User not found: %s", user_id)
                return None
            
            logger.debug("UpdateUserHandler: Retrieved existing user")
            
            # Apply updates (handler responsibility)
            update_data = command.model_dump(exclude_unset=True)
            updated_user = user.model_copy(update=update_data)
            logger.debug("UpdateUserHandler: Applied updates to User model")
            
            # Save via repository (repository handles document conversion)
            saved_user = self.repository.update(user_id, updated_user)
            if not saved_user:
                logger.warning("UpdateUserHandler: Failed to update user %s", user_id)
                return None
            
            # Map to response DTO (handler responsibility)
            response = UserResponse(
                user_id=saved_user.user_id,
                first_name=saved_user.first_name,
                last_name=saved_user.last_name,
                email_address=saved_user.email_address,
                phone_number=saved_user.phone_number,
                account_status="active",
            )
            logger.info("UpdateUserHandler: Successfully updated user %s", user_id)
            
            return response
            
        except Exception as e:
            logger.error("UpdateUserHandler: Failed to update user - %s: %s", type(e).__name__, e)
            raise
