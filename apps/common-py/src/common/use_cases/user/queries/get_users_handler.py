"""Handlers for user query operations - retrieve users from Cosmos DB."""

import logging

from common.infra.repositories import UserRepository
from common.use_cases.user.queries import (
    ListUsersQuery,
    UserListResponse,
    UserResponse,
)

logger = logging.getLogger(__name__)

class GetUsersHandler:
    """Handler for ListUsersQuery - retrieve all users with pagination.
    
    Responsibilities:
    - Accept and validate ListUsersQuery with pagination params
    - Call repository to get paginated users and total count
    - Map documents to User domain models (handler responsibility)
    - Map User models to UserResponse DTOs (handler responsibility)
    - Return UserListResponse with pagination metadata
    """

    def __init__(self, repository: UserRepository):
        """Initialize handler with repository.
        
        Args:
            repository: UserRepository for data access
        """
        self.repository = repository

    def handle(self, query: ListUsersQuery) -> UserListResponse:
        """List users with pagination and sorting.
        .
        
        Flow:
        1. Validate query parameters
        2. Call repository to get users and total count
        3. Map documents → User models (handler responsibility)
        4. Map User models → UserResponse list (handler responsibility)
        5. Return UserListResponse with pagination metadata
        
        Args:
            query: ListUsersQuery DTO with:
                - page: int (1-indexed, default 1)
                - page_size: int (1-100, default 20)
            
        Returns:
            UserListResponse DTO containing:
                - users: list[UserResponse]
                - total: int
                - page: int
                - page_size: int
                - total_pages: int
                
        Example:
            >>> from common.use_cases.user.queries import GetUsersHandler, ListUsersQuery
            >>> from common.infra.repositories import UserRepository
            >>> 
            >>> repository = UserRepository(endpoint, key)
            >>> handler = GetUsersHandler(repository)
            >>> query = ListUsersQuery(page=1, page_size=20)
            >>> response = handler.handle(query)
            >>> print(f"Total users: {response.total}")
        """
        try:
            logger.info("GetUsersHandler: Listing users - page %s, size %s", query.page, query.page_size)
            
            # Calculate offset
            offset = (query.page - 1) * query.page_size
            
            # Get users from repository (returns User models)
            users, total = self.repository.list_all(offset=offset, limit=query.page_size)
            logger.debug("GetUsersHandler: Retrieved %s User models, total: %s", len(users), total)
            
            # Map to response DTOs (handler responsibility)
            user_responses = [
                UserResponse(
                    user_id=user.user_id,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    email_address=user.email_address,
                    phone_number=user.phone_number,
                    account_status="active",
                )
                for user in users
            ]
            
            # Build response with pagination metadata
            total_pages = (total + query.page_size - 1) // query.page_size if total > 0 else 0
            response = UserListResponse(
                users=user_responses,
                total_count=total,
                page=query.page,
                page_size=query.page_size,
                total_pages=total_pages,
                has_next_page=query.page < total_pages,
                has_previous_page=query.page > 1,
            )
            
            logger.info("GetUsersHandler: Successfully listed users - page %s/%s", response.page, response.total_pages)
            return response
            
        except Exception as e:
            logger.error("GetUsersHandler: Failed to list users - %s: %s", type(e).__name__, e)
            raise

