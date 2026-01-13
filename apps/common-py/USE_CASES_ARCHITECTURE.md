# Use Cases Architecture

**Last Updated**: 2025-01-13  
**Purpose**: Explain the use_cases folder structure and how it replaces the previous dtos folder organization

## Overview

The `apps/common-py/src/common/use_cases/` folder contains all **Commands** (write operations) and **Queries** (read operations) organized by business entity or feature.

**Key Changes**:
- ✅ Commands and Queries moved from `dtos/` to `use_cases/`
- ✅ Organized by entity: `use_cases/user/`, `use_cases/document/`, `use_cases/agent/`
- ✅ Base DTOs remain in `dtos/base.py` (shared)
- ✅ Each use case has `commands/` and `queries/` subdirectories

## Folder Structure

```
apps/common-py/src/common/
├── dtos/                      # Base DTO classes (SHARED)
│   ├── base.py                # BaseDTO, BaseCommand, BaseQuery, BaseResponse
│   └── __init__.py
│
├── use_cases/                 # Commands & Queries (ORGANIZED BY ENTITY)
│   ├── user/
│   │   ├── commands/
│   │   │   ├── __init__.py
│   │   │   ├── create_user.py    # CreateUserCommand
│   │   │   ├── update_user.py    # UpdateUserCommand
│   │   │   └── delete_user.py    # DeleteUserCommand
│   │   ├── queries/
│   │   │   ├── __init__.py
│   │   │   ├── get_user.py       # GetUserQuery, UserResponse
│   │   │   ├── list_users.py     # ListUsersQuery, UserListResponse
│   │   │   ├── search_users.py   # SearchUsersQuery
│   │   │   └── responses.py      # All response DTOs (UserResponse, etc.)
│   │   └── __init__.py
│   │
│   ├── document/
│   │   ├── commands/
│   │   │   ├── upload_document.py
│   │   │   └── delete_document.py
│   │   ├── queries/
│   │   │   ├── get_document.py
│   │   │   └── list_documents.py
│   │   └── __init__.py
│   │
│   └── agent/
│       ├── commands/
│       │   └── create_agent.py
│       ├── queries/
│       │   ├── get_agent.py
│       │   └── list_agents.py
│       └── __init__.py
│
├── models/                    # Domain models (User, Document, Agent)
├── services/                  # Business logic
├── repositories/              # Data access
├── mappers/                   # Transformations
└── utils/                     # Utilities
```

## Import Patterns

### Correct: Import from use_cases
```python
# ✅ Correct: Import Commands from use_cases
from common.use_cases.user.commands.create_user import CreateUserCommand
from common.use_cases.user.commands.update_user import UpdateUserCommand
from common.use_cases.user.commands.delete_user import DeleteUserCommand

# ✅ Correct: Import Queries and Responses from use_cases
from common.use_cases.user.queries.get_user import GetUserQuery, UserResponse
from common.use_cases.user.queries.list_users import ListUsersQuery, UserListResponse
from common.use_cases.user.queries.search_users import SearchUsersQuery

# ✅ Correct: Import base DTOs from dtos (shared)
from common.dtos.base import BaseDTO, BaseCommand, BaseQuery, BaseResponse
```

### Incorrect: Don't import from dtos/commands or dtos/queries
```python
# ❌ Wrong: dtos folder no longer contains Commands/Queries
from common.dtos.commands import CreateUserCommand  # This doesn't exist anymore

# ❌ Wrong: dtos folder no longer contains Queries
from common.dtos.queries import GetUserQuery  # This doesn't exist anymore
```

## File Organization Example

### User Create Command
```python
# File: common/use_cases/user/commands/create_user.py
from common.dtos.base import BaseCommand
from pydantic import EmailStr, field_validator

class CreateUserCommand(BaseCommand):
    """Create new user command."""
    first_name: str
    last_name: str
    email_address: EmailStr
    phone_number: str | None = None
    
    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or len(v.strip()) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v.strip()
```

### User Get Query and Response
```python
# File: common/use_cases/user/queries/get_user.py
from datetime import datetime
from common.dtos.base import BaseQuery, BaseResponse
from pydantic import EmailStr

class GetUserQuery(BaseQuery):
    """Get user by ID."""
    user_id: str

class UserResponse(BaseResponse):
    """User response data."""
    user_id: str
    first_name: str
    last_name: str
    email_address: EmailStr
    phone_number: str | None = None
    account_status: str
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None
```

### User List Query and Response
```python
# File: common/use_cases/user/queries/list_users.py
from common.dtos.base import BaseQuery, BaseResponse
from common.use_cases.user.queries.get_user import UserResponse

class ListUsersQuery(BaseQuery):
    """List users with pagination."""
    page: int = 1
    page_size: int = 10
    sort_by: str = "created_at"
    sort_order: str = "asc"

class UserListResponse(BaseResponse):
    """Paginated list of users."""
    users: list[UserResponse]
    total_count: int
    has_next_page: bool
    has_previous_page: bool
```

## Exports via __init__.py

### User Commands Export
```python
# File: common/use_cases/user/commands/__init__.py
from common.use_cases.user.commands.create_user import CreateUserCommand
from common.use_cases.user.commands.update_user import UpdateUserCommand
from common.use_cases.user.commands.delete_user import DeleteUserCommand

__all__ = [
    "CreateUserCommand",
    "UpdateUserCommand",
    "DeleteUserCommand",
]
```

### User Queries Export
```python
# File: common/use_cases/user/queries/__init__.py
from common.use_cases.user.queries.get_user import GetUserQuery, UserResponse
from common.use_cases.user.queries.list_users import ListUsersQuery, UserListResponse
from common.use_cases.user.queries.search_users import SearchUsersQuery

__all__ = [
    "GetUserQuery",
    "ListUsersQuery",
    "SearchUsersQuery",
    "UserResponse",
    "UserListResponse",
]
```

### User Module Export
```python
# File: common/use_cases/user/__init__.py
from common.use_cases.user.commands import *
from common.use_cases.user.queries import *

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
```

## Benefits of use_cases Organization

1. **Clearer Intent**: Each use case (create user, get user, list users) has its own file
2. **Easier Scaling**: Adding new entities (Document, Agent) is straightforward
3. **Better Testing**: Each use case can be tested independently
4. **Reduced Imports**: Import exactly what you need from each use case
5. **Feature-Focused**: Organized around business features, not technical layers

## Migration from Old Structure

### Before (dtos folder)
```
dtos/
├── commands/
│   └── user_commands.py  # Multiple commands in one file
├── queries/
│   └── user_queries.py   # Multiple queries in one file
└── base.py
```

### After (use_cases folder)
```
use_cases/
└── user/
    ├── commands/
    │   ├── create_user.py     # One command per file
    │   ├── update_user.py
    │   └── delete_user.py
    ├── queries/
    │   ├── get_user.py        # One query per file
    │   ├── list_users.py
    │   └── search_users.py
    └── __init__.py
```

## FastAPI Route Integration

```python
# File: apps/api/src/api/routes/users.py
from fastapi import APIRouter, HTTPException
from common.use_cases.user.commands.create_user import CreateUserCommand
from common.use_cases.user.queries.get_user import GetUserQuery, UserResponse
from common.use_cases.user.queries.list_users import ListUsersQuery, UserListResponse
from src.api.services.user_service import UserService

router = APIRouter(prefix="/api/users", tags=["users"])
service = UserService()

@router.post("", response_model=UserResponse, status_code=201)
async def create_user(command: CreateUserCommand) -> UserResponse:
    """Create a new user."""
    return await service.create_user(command)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str) -> UserResponse:
    """Get user by ID."""
    return await service.get_user(GetUserQuery(user_id=user_id))

@router.get("", response_model=UserListResponse)
async def list_users(page: int = 1, page_size: int = 10) -> UserListResponse:
    """List users with pagination."""
    return await service.list_users(
        ListUsersQuery(page=page, page_size=page_size)
    )
```

## Testing Pattern

```python
# File: tests/use_cases/user/test_create_user.py
import pytest
from common.use_cases.user.commands.create_user import CreateUserCommand
from common.services.user_service import UserService

@pytest.mark.asyncio
async def test_create_user_command():
    """Test CreateUserCommand validation."""
    command = CreateUserCommand(
        first_name="Jane",
        last_name="Doe",
        email_address="jane@example.com"
    )
    
    assert command.first_name == "Jane"
    assert command.email_address == "jane@example.com"

@pytest.mark.asyncio
async def test_create_user_service():
    """Test service accepts command and returns response."""
    service = UserService()
    command = CreateUserCommand(
        first_name="Jane",
        last_name="Doe",
        email_address="jane@example.com"
    )
    
    response = await service.create_user(command)
    
    assert response.user_id is not None
    assert response.first_name == "Jane"
```

## Rules & Best Practices

1. **One file per use case**: Don't put multiple commands in one file
2. **Separate commands and queries**: Keep write and read operations separate
3. **Response DTOs in queries folder**: Responses belong with read operations
4. **Import from use_cases**: Never import from dtos/commands or dtos/queries
5. **Export via __init__.py**: Make imports convenient and centralized
6. **Name files after use case**: `create_user.py`, not `user_create.py`
7. **Preserve naming conventions**: All Python naming rules apply (snake_case fields, PascalCase classes, camelCase JSON)

---

**Version**: 1.0  
**Related**: [constitution-python.md](constitution-python.md), [constitution-api.md](constitution-api.md)
