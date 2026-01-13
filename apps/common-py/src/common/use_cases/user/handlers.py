"""User handlers - convenient imports for all user use case handlers.

This module provides a central location to import all user handlers.
Handlers are organized in their respective command/query folders but exported here for convenience.
"""

from .commands import CreateUserHandler, UpdateUserHandler, DeleteUserHandler
from .queries import GetUserHandler, GetUsersHandler, SearchUsersHandler

__all__ = [
    # Command handlers (write operations)
    "CreateUserHandler",
    "UpdateUserHandler",
    "DeleteUserHandler",
    # Query handlers (read operations)
    "GetUserHandler",
    "GetUsersHandler",
    "SearchUsersHandler",
]
