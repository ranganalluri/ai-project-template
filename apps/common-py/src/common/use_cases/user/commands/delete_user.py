"""DeleteUserCommand - delete an existing user."""

from common.dtos.base import BaseCommand

class DeleteUserCommand(BaseCommand):
    """Command to delete an existing user.
    
    Since the user_id comes from the route parameter, this command
    is minimal. It serves as a marker for the delete operation.
    
    Example:
        >>> from common.use_cases.user.commands import DeleteUserCommand, DeleteUserHandler
        >>> from common.infra.repositories import UserRepository
        >>> 
        >>> repository = UserRepository(endpoint, key)
        >>> handler = DeleteUserHandler(repository)
        >>> command = DeleteUserCommand()
        >>> success = handler.handle("user-123", command)
        >>> if success:
        ...     print("User deleted")
    """
    
    model_config = {
        "json_schema_extra": {
            "example": {}
        }
    }
