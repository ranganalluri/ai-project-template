"""Data Transfer Objects for commands and queries."""

from common.dtos.commands import (
    CreateUserCommand,
    UpdateUserCommand,
    DeleteUserCommand,
)
from common.dtos.queries import (
    GetUserQuery,
    ListUsersQuery,
    SearchUsersQuery,
    UserResponse,
    UserListResponse,
)

__all__ = [
    # Commands
    "CreateUserCommand",
    "UpdateUserCommand",
    "DeleteUserCommand",
    # Queries
    "GetUserQuery",
    "ListUsersQuery",
    "SearchUsersQuery",
    # Responses
    "UserResponse",
    "UserListResponse",
]
