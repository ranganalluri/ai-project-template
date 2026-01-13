"""Handler for SearchUsersQuery - search users by name."""

import logging

from common.use_cases.user.queries import SearchUsersQuery, UserResponse, UserListResponse
from common.models.user import User
from common.infra.repositories import UserRepository

logger = logging.getLogger(__name__)


class SearchUsersHandler:
    """Handler for searching users by name.
    
    Responsibilities:
    - Accept and validate SearchUsersQuery
    - Call repository to search users
    - Map documents to User domain models (handler responsibility)
    - Map User models to UserResponse DTOs (handler responsibility)
    - Return UserListResponse with search results and pagination
    """

    def __init__(self, repository: UserRepository):
        """Initialize handler with repository.
        
        Args:
            repository: UserRepository for data access
        """
        self.repository = repository

    def handle(self, query: SearchUsersQuery) -> UserListResponse:
        """Search users by name with pagination.
        
        Flow:
        1. Validate query (name, page, page_size)
        2. Call repository to search users
        3. Map documents → User models (handler responsibility)
        4. Map User models → UserResponse list (handler responsibility)
        5. Return UserListResponse with pagination metadata
        
        Args:
            query: SearchUsersQuery DTO with:
                - name: str (search term)
                - page: int (1-indexed)
                - page_size: int
            
        Returns:
            UserListResponse DTO with search results
                
        Example:
            >>> from common.use_cases.user.queries import SearchUsersHandler, SearchUsersQuery
            >>> from common.infra.repositories import UserRepository
            >>> 
            >>> repository = UserRepository(endpoint, key)
            >>> handler = SearchUsersHandler(repository)
            >>> query = SearchUsersQuery(search_term="Jane", page=1, page_size=20)
            >>> response = handler.handle(query)
            >>> print(f"Found {response.total} users matching 'Jane'")
        """
        try:
            logger.info(f"SearchUsersHandler: Searching for '{query.search_term}' - page {query.page}")
            
            # Calculate offset
            offset = (query.page - 1) * query.page_size
            
            # Search via repository (returns User models)
            users, total = self.repository.search_by_name(
                search_term=query.search_term,
                offset=offset,
                limit=query.page_size
            )
            logger.debug("SearchUsersHandler: Retrieved %s User models, total: %s", len(users), total)
            
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
            
            logger.info("SearchUsersHandler: Found %s users matching '%s'", total, query.search_term)
            return response
            
        except ValueError:
            logger.warning("SearchUsersHandler: Validation error for search_term='%s'", query.search_term)
            raise
        except Exception as e:
            logger.error("SearchUsersHandler: Failed to search users - %s: %s", type(e).__name__, e)
            raise
