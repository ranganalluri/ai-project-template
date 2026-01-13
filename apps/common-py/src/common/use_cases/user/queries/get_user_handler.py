"""Handler for GetUserQuery - retrieve single user by ID."""

import logging

from common.use_cases.user.queries import GetUserQuery, UserResponse
from common.models.user import User
from common.infra.repositories import UserRepository

logger = logging.getLogger(__name__)


class GetUserHandler:
    """Handler for retrieving a single user by ID.
    
    Responsibilities:
    - Accept and validate GetUserQuery
    - Call repository to get user by ID
    - Map document to User domain model (handler responsibility)
    - Map User model to UserResponse DTO (handler responsibility)
    - Return UserResponse or None if not found
    """

    def __init__(self, repository: UserRepository):
        """Initialize handler with repository.
        
        Args:
            repository: UserRepository for data access
        """
        self.repository = repository

    def handle(self, query: GetUserQuery) -> UserResponse | None:
        """Get a single user by ID.
        
        Flow:
        1. Validate query (user_id)
        2. Call repository to get User model (repository handles document conversion)
        3. Map User model → UserResponse (handler responsibility)
        4. Return None if user not found
        
        Args:
            query: GetUserQuery DTO with:
                - user_id: str (required)
            
        Returns:
            UserResponse DTO or None if not found
                
        Example:
            >>> from common.use_cases.user.queries import GetUserHandler, GetUserQuery
            >>> from common.infra.repositories import UserRepository
            >>> 
            >>> repository = UserRepository(endpoint, key)
            >>> handler = GetUserHandler(repository)
            >>> query = GetUserQuery(user_id="user-123")
            >>> response = handler.handle(query)
            >>> if response:
            ...     print(f"Found user: {response.name}")
            ... else:
            ...     print("User not found")
        """
        try:
            logger.info(f"GetUserHandler: Fetching user {query.user_id}")
            
            # Get user from repository (returns User model)
            user = self.repository.get_by_id(query.user_id)
            if not user:
                logger.warning(f"GetUserHandler: User not found: {query.user_id}")
                return None
            
            logger.debug(f"GetUserHandler: Retrieved User model")
            
            # Map to response DTO (handler responsibility)
            response = UserResponse(
                user_id=user.user_id,
                name=user.name,
                email=user.email,
            )
            logger.info(f"GetUserHandler: Successfully retrieved user {query.user_id}")
            
            return response
            
        except Exception as e:
            logger.error(f"GetUserHandler: Failed to get user - {type(e).__name__}: {str(e)}")
            raise
