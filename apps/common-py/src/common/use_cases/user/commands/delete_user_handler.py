"""Handler for DeleteUserCommand - deletes users from Cosmos DB."""

import logging

from common.use_cases.user.commands.delete_user import DeleteUserCommand
from common.infra.repositories import UserRepository

logger = logging.getLogger(__name__)


class DeleteUserHandler:
    """Handler for deleting users.
    
    Responsibilities:
    - Accept user_id
    - Call repository to delete user
    - Return success/failure status
    """

    def __init__(self, repository: UserRepository):
        """Initialize handler with repository.
        
        Args:
            repository: UserRepository for data access
        """
        self.repository = repository

    def handle(self, user_id: str, command: DeleteUserCommand) -> bool:
        """Delete a user by ID.
        
        Flow:
        1. Call repository to delete user
        2. Return True if deleted, False if not found
        
        Args:
            user_id: User ID to delete
            command: DeleteUserCommand marker
            
        Returns:
            True if deleted, False if not found
                
        Example:
            >>> from common.use_cases.user.commands import DeleteUserHandler, DeleteUserCommand
            >>> from common.infra.repositories import UserRepository
            >>> 
            >>> repository = UserRepository(endpoint, key)
            >>> handler = DeleteUserHandler(repository)
            >>> command = DeleteUserCommand()
            >>> success = handler.handle("user-123", command)
            >>> if success:
            ...     print("User deleted")
            ... else:
            ...     print("User not found")
        """
        try:
            logger.info(f"DeleteUserHandler: Deleting user {user_id}")
            
            # Delete via repository
            success = self.repository.delete(user_id)
            
            if success:
                logger.info(f"DeleteUserHandler: Successfully deleted user {user_id}")
            else:
                logger.warning(f"DeleteUserHandler: User not found for deletion: {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"DeleteUserHandler: Failed to delete user - {type(e).__name__}: {str(e)}")
            raise
