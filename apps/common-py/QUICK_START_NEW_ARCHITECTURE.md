"""
QUICK START: NEW LAYERED ARCHITECTURE
=====================================

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                             │
│  (FastAPI Routes - HTTP concerns, validation, responses)     │
│  Location: apps/api/src/api/routes/                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓ calls
┌─────────────────────────────────────────────────────────────┐
│                    Use Case Layer                            │
│  (Handlers - business logic, mapping, orchestration)         │
│  Location: apps/common-py/src/common/use_cases/             │
│  • Commands (write) → commands/*_handler.py                  │
│  • Queries (read) → queries/*_handler.py                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓ calls
┌─────────────────────────────────────────────────────────────┐
│                 Infrastructure Layer                         │
│  (Repository - data access, persistence, DB operations)      │
│  Location: apps/common-py/src/common/infra/repositories/    │
└─────────────────────────────────────────────────────────────┘
```

## Quick Usage Examples

### 1. Create User (Command)

```python
from common.use_cases.user.commands import CreateUserCommand, CreateUserHandler
from common.infra.repositories import UserRepository

# Initialize
repository = UserRepository(endpoint, key)
handler = CreateUserHandler(repository)

# Execute
command = CreateUserCommand(name="Jane Doe", email="jane@example.com")
response = handler.handle(command)  # Returns UserResponse
print(f"Created: {response.user_id}")
```

### 2. Get User (Query)

```python
from common.use_cases.user.queries import GetUserQuery, GetUserHandler
from common.infra.repositories import UserRepository

# Initialize
repository = UserRepository(endpoint, key)
handler = GetUserHandler(repository)

# Execute
query = GetUserQuery(user_id="user-123")
response = handler.handle(query)  # Returns UserResponse | None
if response:
    print(f"Found: {response.name}")
else:
    print("User not found")
```

### 3. List Users (Query with Pagination)

```python
from common.use_cases.user.queries import ListUsersQuery, GetUsersHandler
from common.infra.repositories import UserRepository

# Initialize
repository = UserRepository(endpoint, key)
handler = GetUsersHandler(repository)

# Execute
query = ListUsersQuery(page=1, page_size=20)
response = handler.handle(query)  # Returns UserListResponse
print(f"Total: {response.total}, Page: {response.page}/{response.total_pages}")
for user in response.users:
    print(f"  - {user.name} ({user.email})")
```

### 4. Update User (Command)

```python
from common.use_cases.user.commands import UpdateUserCommand, UpdateUserHandler
from common.infra.repositories import UserRepository

# Initialize
repository = UserRepository(endpoint, key)
handler = UpdateUserHandler(repository)

# Execute
command = UpdateUserCommand(name="Jane Smith")  # Only update name
response = handler.handle("user-123", command)  # Returns UserResponse | None
if response:
    print(f"Updated: {response.name}")
```

### 5. Delete User (Command)

```python
from common.use_cases.user.commands import DeleteUserHandler
from common.infra.repositories import UserRepository

# Initialize
repository = UserRepository(endpoint, key)
handler = DeleteUserHandler(repository)

# Execute
success = handler.handle("user-123")  # Returns bool
if success:
    print("User deleted")
else:
    print("User not found")
```

### 6. Search Users (Query)

```python
from common.use_cases.user.queries import SearchUsersQuery, SearchUsersHandler
from common.infra.repositories import UserRepository

# Initialize
repository = UserRepository(endpoint, key)
handler = SearchUsersHandler(repository)

# Execute
query = SearchUsersQuery(name="Jane", page=1, page_size=10)
response = handler.handle(query)  # Returns UserListResponse
print(f"Found {response.total} users matching 'Jane'")
```

## FastAPI Integration

### Step 1: Create Repository Dependency

```python
# apps/api/src/api/services/__init__.py

from common.infra.repositories import UserRepository
from api.config import Settings, get_settings
from fastapi import Depends

_cache = {}

def get_user_repository(settings: Settings = Depends(get_settings)) -> UserRepository:
    """Dependency for UserRepository."""
    if "user_repository" not in _cache:
        _cache["user_repository"] = UserRepository(
            cosmos_endpoint=settings.azure_cosmosdb_endpoint,
            cosmos_key=settings.azure_cosmosdb_key,
            database_name=settings.database_name,
            container_name=settings.cosmos_users_container,
            use_managed_identity=settings.azure_cosmosdb_key is None,
        )
    return _cache["user_repository"]
```

### Step 2: Use in Routes

```python
# apps/api/src/api/routes/user.py

from fastapi import APIRouter, Depends, HTTPException, status
from api.services import get_user_repository
from common.infra.repositories import UserRepository
from common.use_cases.user.commands import (
    CreateUserCommand, CreateUserHandler,
    UpdateUserCommand, UpdateUserHandler,
    DeleteUserHandler
)
from common.use_cases.user.queries import (
    GetUserQuery, GetUserHandler,
    ListUsersQuery, GetUsersHandler,
    SearchUsersQuery, SearchUsersHandler,
    UserResponse, UserListResponse
)

router = APIRouter(prefix="/users", tags=["users"])

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    command: CreateUserCommand,
    repository: UserRepository = Depends(get_user_repository)
):
    """Create new user."""
    handler = CreateUserHandler(repository)
    return handler.handle(command)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    repository: UserRepository = Depends(get_user_repository)
):
    """Get user by ID."""
    handler = GetUserHandler(repository)
    query = GetUserQuery(user_id=user_id)
    response = handler.handle(query)
    if not response:
        raise HTTPException(status_code=404, detail="User not found")
    return response

@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    repository: UserRepository = Depends(get_user_repository)
):
    """List all users with pagination."""
    handler = GetUsersHandler(repository)
    query = ListUsersQuery(page=page, page_size=page_size)
    return handler.handle(query)

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    command: UpdateUserCommand,
    repository: UserRepository = Depends(get_user_repository)
):
    """Update existing user."""
    handler = UpdateUserHandler(repository)
    response = handler.handle(user_id, command)
    if not response:
        raise HTTPException(status_code=404, detail="User not found")
    return response

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    repository: UserRepository = Depends(get_user_repository)
):
    """Delete user."""
    handler = DeleteUserHandler(repository)
    success = handler.handle(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")

@router.get("/search", response_model=UserListResponse)
async def search_users(
    name: str,
    page: int = 1,
    page_size: int = 10,
    repository: UserRepository = Depends(get_user_repository)
):
    """Search users by name."""
    handler = SearchUsersHandler(repository)
    query = SearchUsersQuery(name=name, page=page, page_size=page_size)
    return handler.handle(query)
```

## Key Concepts

### 1. Handlers Do Mapping
Handlers are responsible for all transformations:
- **DTO → Domain Model**: CreateUserCommand → User
- **Domain Model → Document**: User → Cosmos dict
- **Document → Domain Model**: Cosmos dict → User
- **Domain Model → DTO**: User → UserResponse

### 2. Repository is Pure Data Access
Repository only interacts with Cosmos DB:
- No business logic
- No mapping logic
- Returns raw documents (dict) or simple types
- Handles database exceptions

### 3. Commands vs Queries
- **Commands** (write): Create, Update, Delete
- **Queries** (read): Get, List, Search
- Separate folders, separate handlers
- CQRS-inspired pattern

### 4. DTOs for API Contracts
- **Commands**: Input for write operations
- **Queries**: Input for read operations
- **Responses**: Output from all operations
- Pydantic validation + naming conventions

## File Structure

```
apps/common-py/src/common/
├── infra/
│   └── repositories/
│       ├── __init__.py                    # Exports UserRepository
│       └── user_repository.py             # Data access layer
│
├── use_cases/
│   └── user/
│       ├── commands/
│       │   ├── __init__.py                # Exports commands + handlers
│       │   ├── create_user.py             # CreateUserCommand DTO
│       │   ├── create_user_handler.py     # CreateUserHandler
│       │   ├── update_user_handler.py     # UpdateUserHandler
│       │   └── delete_user_handler.py     # DeleteUserHandler
│       │
│       ├── queries/
│       │   ├── __init__.py                # Exports queries + handlers
│       │   ├── get_user.py                # GetUserQuery DTO
│       │   ├── list_users.py              # ListUsersQuery DTO
│       │   ├── search_users.py            # SearchUsersQuery DTO
│       │   ├── responses.py               # UserResponse, UserListResponse
│       │   ├── get_user_handler.py        # GetUserHandler
│       │   ├── get_users_handler.py       # GetUsersHandler
│       │   └── search_users_handler.py    # SearchUsersHandler
│       │
│       └── handlers.py                    # Convenience: exports all handlers
│
└── models/
    └── user.py                            # User domain model
```

## Testing Strategy

### Unit Test Handler (Mock Repository)
```python
from unittest.mock import Mock
from common.use_cases.user.commands import CreateUserHandler, CreateUserCommand

def test_create_user_handler():
    # Mock repository
    mock_repo = Mock()
    mock_repo.create.return_value = {
        "id": "user-123",
        "user_id": "user-123",
        "name": "Jane Doe",
        "email": "jane@example.com"
    }
    
    # Test handler
    handler = CreateUserHandler(mock_repo)
    command = CreateUserCommand(name="Jane Doe", email="jane@example.com")
    response = handler.handle(command)
    
    # Verify
    assert response.name == "Jane Doe"
    assert mock_repo.create.called
```

### Integration Test (Real Cosmos DB)
```python
import pytest
from common.infra.repositories import UserRepository
from common.use_cases.user.commands import CreateUserHandler, CreateUserCommand

@pytest.fixture
def repository():
    return UserRepository(endpoint=..., key=...)

def test_create_user_integration(repository):
    handler = CreateUserHandler(repository)
    command = CreateUserCommand(name="Test User", email="test@example.com")
    response = handler.handle(command)
    
    assert response.user_id is not None
    # Cleanup
    repository.delete(response.user_id)
```

## Common Patterns

### Error Handling
```python
try:
    handler = CreateUserHandler(repository)
    response = handler.handle(command)
except ValueError as e:
    # Business logic errors (duplicate email, etc.)
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    # Infrastructure errors (Cosmos DB down, etc.)
    logger.error(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

### Logging
All handlers include structured logging:
```python
logger.info(f"Creating user: {command.email}")      # Operations
logger.debug(f"Mapped to User model")               # Transformations
logger.warning(f"User not found: {user_id}")        # Expected failures
logger.error(f"Failed to create user: {e}")         # Unexpected failures
```

### Pagination
```python
query = ListUsersQuery(page=1, page_size=20)
response = handler.handle(query)
# response.total, response.page, response.page_size, response.total_pages
```

## Next Steps

1. ✅ Repository layer created
2. ✅ Handlers updated with mapping logic
3. ⏳ Update API to use repository + handlers (see examples above)
4. ⏳ Remove old UserService and UserMapper
5. ⏳ Update tests
6. ⏳ Update documentation
