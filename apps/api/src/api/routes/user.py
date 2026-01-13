"""User API routes."""

from api.dependencies import (
    get_create_user_handler,
    get_delete_user_handler,
    get_get_users_handler,
    get_search_users_handler,
)
from common.use_cases.user.commands import CreateUserCommand, DeleteUserCommand
from common.use_cases.user.queries import (
    ListUsersQuery,
    SearchUsersQuery,
    UserListResponse,
    UserResponse,
)
from common.use_cases.user.commands.create_user_handler import CreateUserHandler
from common.use_cases.user.commands.delete_user_handler import DeleteUserHandler
from common.use_cases.user.queries.get_users_handler import GetUsersHandler
from common.use_cases.user.queries.search_users_handler import SearchUsersHandler
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/users", tags=["users"], redirect_slashes=False)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    command: CreateUserCommand,
    handler: CreateUserHandler = Depends(get_create_user_handler),
) -> UserResponse:
    """Create a new user.
    
    Request body (camelCase JSON):
    {
        "name": "Jane Doe",
        "email": "jane@example.com"
    }
    """
    try:
        return handler.handle(command)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=UserListResponse)
@router.get("/", response_model=UserListResponse)
async def list_users(
    query: ListUsersQuery = Depends(),
    handler: GetUsersHandler = Depends(get_get_users_handler),
) -> UserListResponse:
    """List all users with pagination.
    
    Query parameters:
    - page: Page number (default: 1)
    - page_size: Page size (default: 10)
    """
    return handler.handle(query)


@router.get("/search", response_model=UserListResponse)
async def search_users(
    query: SearchUsersQuery = Depends(),
    handler: SearchUsersHandler = Depends(get_search_users_handler),
) -> UserListResponse:
    """Search users by search term.
    
    Query parameters:
    - search_term: Search term (required, min 1 char)
    - page: Page number (default: 1)
    - page_size: Page size (default: 20, max: 100)
    """
    return handler.handle(query)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    handler: DeleteUserHandler = Depends(get_delete_user_handler),
):
    """Delete a user by ID using DeleteUserCommand."""
    command = DeleteUserCommand()

    if not handler.handle(user_id, command):
        raise HTTPException(status_code=404, detail="User not found.")
    return None
