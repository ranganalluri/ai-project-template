# Layered Architecture Pattern - Python Backend

**Status**: CURRENT (Replaces service+mapper pattern)  
**Last Updated**: 2025-01-13  
**Applies To**: All Python services (API, Common-py, Functions, MCP)

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                    API Layer                              │
│  (FastAPI Routes - HTTP, validation, status codes)        │
│  Location: apps/api/src/api/routes/                      │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ↓ calls handlers
┌──────────────────────────────────────────────────────────┐
│                 Use Case Layer                            │
│  (Handlers - business logic, mapping, orchestration)      │
│  Location: apps/common-py/src/common/use_cases/          │
│  • Commands (write): commands/*_handler.py                │
│  • Queries (read): queries/*_handler.py                   │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ↓ calls repository
┌──────────────────────────────────────────────────────────┐
│              Infrastructure Layer                         │
│  (Repository - data access, Cosmos DB operations)         │
│  Location: apps/common-py/src/common/infra/repositories/ │
└──────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### API Layer (apps/api/src/api/routes/)

**Purpose**: HTTP request/response handling

**Responsibilities**:
- FastAPI route definitions
- HTTP status codes (200, 201, 404, 400, 500)
- Query parameter parsing
- Dependency injection
- OpenAPI documentation
- **Does NOT** contain business logic or mapping

**Example**:
```python
# apps/api/src/api/routes/user.py
from fastapi import APIRouter, Depends, HTTPException, status
from api.services import get_user_repository
from common.infra.repositories import UserRepository
from common.use_cases.user.commands import CreateUserCommand, CreateUserHandler
from common.use_cases.user.queries import GetUserQuery, GetUserHandler, UserResponse

router = APIRouter(prefix="/users", tags=["users"])

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    command: CreateUserCommand,
    repository: UserRepository = Depends(get_user_repository)
):
    """Thin API layer - delegates immediately to handler."""
    handler = CreateUserHandler(repository)
    return handler.handle(command)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    repository: UserRepository = Depends(get_user_repository)
):
    """Thin API layer - delegates immediately to handler."""
    handler = GetUserHandler(repository)
    query = GetUserQuery(user_id=user_id)
    response = handler.handle(query)
    if not response:
        raise HTTPException(status_code=404, detail="User not found")
    return response
```

### Use Case Layer (apps/common-py/src/common/use_cases/)

**Purpose**: Business logic and all mapping

**Responsibilities**:
- Accept and validate DTOs (Commands/Queries)
- **Map DTO → Domain Model** (handler responsibility)
- **Map Domain Model → Database Document** (handler responsibility)
- **Map Document → Domain Model** (handler responsibility)
- **Map Domain Model → Response DTO** (handler responsibility)
- Call repository for data access
- Business logic and orchestration
- Logging and error handling

**Key Rule**: **Handlers own ALL mapping logic** - no external mapper classes

**Command Handler Example** (Write Operation):
```python
# apps/common-py/src/common/use_cases/user/commands/create_user_handler.py
from uuid import uuid4
from common.use_cases.user.commands import CreateUserCommand
from common.use_cases.user.queries import UserResponse
from common.models.user import User
from common.infra.repositories import UserRepository

class CreateUserHandler:
    """Handler for creating users - includes ALL mapping logic."""
    
    def __init__(self, repository: UserRepository):
        self.repository = repository
    
    def handle(self, command: CreateUserCommand) -> UserResponse:
        logger.info(f"Creating user: {command.email}")
        
        # 1. Map Command → Domain Model (handler responsibility)
        user = User(
            user_id=f"user-{uuid4()}",
            name=command.name,
            email=command.email,
        )
        
        # 2. Map Domain Model → Cosmos Document (handler responsibility)
        user_doc = {
            "id": user.user_id,
            "user_id": user.user_id,
            **user.model_dump(),
        }
        
        # 3. Save via repository
        self.repository.create(user_doc)
        
        # 4. Map Domain Model → Response DTO (handler responsibility)
        return UserResponse(
            user_id=user.user_id,
            name=user.name,
            email=user.email,
        )
```

**Query Handler Example** (Read Operation):
```python
# apps/common-py/src/common/use_cases/user/queries/get_users_handler.py
from common.use_cases.user.queries import ListUsersQuery, UserResponse, UserListResponse
from common.models.user import User
from common.infra.repositories import UserRepository

class GetUsersHandler:
    """Handler for listing users - includes ALL mapping logic."""
    
    def __init__(self, repository: UserRepository):
        self.repository = repository
    
    def handle(self, query: ListUsersQuery) -> UserListResponse:
        logger.info(f"Listing users: page {query.page}")
        
        # 1. Get data from repository
        offset = (query.page - 1) * query.page_size
        items, total = self.repository.list_all(offset=offset, limit=query.page_size)
        
        # 2. Map Documents → Domain Models (handler responsibility)
        users = [
            User(
                user_id=doc["user_id"],
                name=doc["name"],
                email=doc["email"],
            )
            for doc in items
        ]
        
        # 3. Map Domain Models → Response DTOs (handler responsibility)
        user_responses = [
            UserResponse(
                user_id=user.user_id,
                name=user.name,
                email=user.email,
            )
            for user in users
        ]
        
        # 4. Build pagination response
        total_pages = (total + query.page_size - 1) // query.page_size if total > 0 else 0
        return UserListResponse(
            users=user_responses,
            total=total,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages,
        )
```

### Infrastructure Layer (apps/common-py/src/common/infra/repositories/)

**Purpose**: Pure data access

**Responsibilities**:
- Direct Cosmos DB operations (create, read, update, delete, query)
- Connection management and pooling
- Database-level error handling
- Retry logic
- Returns raw documents (dict), counts, or booleans
- **Does NOT** contain mapping or business logic

**Example**:
```python
# apps/common-py/src/common/infra/repositories/user_repository.py
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosAccessConditionFailedError

class UserRepository:
    """Pure data access - no mapping, no business logic."""
    
    def __init__(self, cosmos_endpoint: str, cosmos_key: str, ...):
        self.client = CosmosClient(cosmos_endpoint, cosmos_key)
        self.container = self.client.get_database_client(db).get_container_client(container)
    
    def create(self, user_doc: dict) -> dict:
        """Create document. Returns created document."""
        return self.container.create_item(
            body=user_doc,
            enable_automatic_id_generation=False
        )
    
    def get_by_id(self, user_id: str) -> dict | None:
        """Get document by ID. Returns dict or None."""
        try:
            return self.container.read_item(item=user_id, partition_key=user_id)
        except CosmosResourceNotFoundError:
            return None
    
    def list_all(self, offset: int, limit: int) -> tuple[list[dict], int]:
        """List documents with pagination. Returns (items, total_count)."""
        # Get total count
        count_query = "SELECT VALUE COUNT(1) FROM c"
        total = list(self.container.query_items(
            query=count_query,
            enable_cross_partition_query=True
        ))[0]
        
        # Get paginated results
        sql_query = f"SELECT * FROM c OFFSET {offset} LIMIT {limit}"
        items = list(self.container.query_items(
            query=sql_query,
            enable_cross_partition_query=True
        ))
        
        return items, total
    
    def update(self, user_id: str, user_doc: dict) -> dict | None:
        """Update document. Returns updated document or None."""
        try:
            return self.container.replace_item(item=user_id, body=user_doc)
        except CosmosResourceNotFoundError:
            return None
    
    def delete(self, user_id: str) -> bool:
        """Delete document. Returns True if deleted, False if not found."""
        try:
            self.container.delete_item(item=user_id, partition_key=user_id)
            return True
        except CosmosResourceNotFoundError:
            return False
```

## Folder Structure

### Use Cases Organization

```
apps/common-py/src/common/use_cases/
└── user/                              # Entity-specific use cases
    ├── __init__.py                    # Exports all DTOs and handlers
    ├── handlers.py                    # Convenience: exports all handlers
    │
    ├── commands/                      # Write operations
    │   ├── __init__.py                # Exports commands + handlers
    │   ├── create_user.py             # CreateUserCommand DTO
    │   ├── create_user_handler.py     # CreateUserHandler (includes mapping)
    │   ├── update_user_handler.py     # UpdateUserHandler (includes mapping)
    │   └── delete_user_handler.py     # DeleteUserHandler
    │
    └── queries/                       # Read operations
        ├── __init__.py                # Exports queries + handlers + responses
        ├── get_user.py                # GetUserQuery DTO
        ├── list_users.py              # ListUsersQuery DTO
        ├── search_users.py            # SearchUsersQuery DTO
        ├── responses.py               # UserResponse, UserListResponse DTOs
        ├── get_user_handler.py        # GetUserHandler (includes mapping)
        ├── get_users_handler.py       # GetUsersHandler (includes mapping)
        └── search_users_handler.py    # SearchUsersHandler (includes mapping)
```

### Repository Organization

```
apps/common-py/src/common/infra/
└── repositories/
    ├── __init__.py                    # Exports all repositories
    ├── user_repository.py             # UserRepository
    ├── document_repository.py         # DocumentRepository (future)
    └── agent_repository.py            # AgentRepository (future)
```

## Key Architectural Rules

1. **Handlers Own Mapping**: ALL transformation logic (DTO ↔ Model ↔ Document) lives in handlers
2. **Repository is Pure Data**: Only Cosmos DB operations, no business logic or mapping
3. **API is Thin**: Only HTTP concerns, delegates to handlers immediately
4. **Single Responsibility**: Each handler does ONE operation (Create, Get, List, Update, Delete, Search)
5. **Dependency Flow**: API → Handler → Repository (never skip layers)
6. **No Mapper Classes**: Mapping is inline in handlers, not in separate utility classes
7. **Commands vs Queries**: Separate folders and handlers for write vs read operations
8. **CQRS-Inspired**: Commands (write) and Queries (read) are separate and independent

## Imports and Exports

### Handlers Export Pattern

```python
# apps/common-py/src/common/use_cases/user/commands/__init__.py
from .create_user import CreateUserCommand
from .create_user_handler import CreateUserHandler
from .update_user_handler import UpdateUserHandler
from .delete_user_handler import DeleteUserHandler

__all__ = [
    "CreateUserCommand",
    "CreateUserHandler",
    "UpdateUserHandler",
    "DeleteUserHandler",
]
```

```python
# apps/common-py/src/common/use_cases/user/queries/__init__.py
from .get_user import GetUserQuery
from .list_users import ListUsersQuery
from .search_users import SearchUsersQuery
from .responses import UserResponse, UserListResponse
from .get_user_handler import GetUserHandler
from .get_users_handler import GetUsersHandler
from .search_users_handler import SearchUsersHandler

__all__ = [
    "GetUserQuery",
    "ListUsersQuery",
    "SearchUsersQuery",
    "UserResponse",
    "UserListResponse",
    "GetUserHandler",
    "GetUsersHandler",
    "SearchUsersHandler",
]
```

### Usage in API Routes

```python
# Preferred: Import from specific modules
from common.use_cases.user.commands import CreateUserCommand, CreateUserHandler
from common.use_cases.user.queries import GetUserQuery, GetUserHandler

# Alternative: Import from convenience module
from common.use_cases.user.handlers import (
    CreateUserHandler,
    GetUserHandler,
    GetUsersHandler,
    UpdateUserHandler,
    DeleteUserHandler,
    SearchUsersHandler,
)
```

## Migration from Old Pattern

### OLD Pattern (Deprecated)

```
API → UserService → UserMapper → Cosmos Container
```

**Problems**:
- Mapping logic scattered in separate utility class
- Service layer mixed business logic with data access
- Direct container access from service
- Harder to test and mock

**Files to Remove/Deprecate**:
- `services/user_service.py` - Replace with repository + handlers
- `utils/user_mapper.py` - Mapping logic moved into handlers
- `mappers/` folder - No longer needed

### NEW Pattern (Current)

```
API → Handler (includes mapping) → UserRepository → Cosmos DB
```

**Benefits**:
- Handlers own their mapping logic (co-located, easier to maintain)
- Repository is pure data access (easy to test)
- Clear separation of concerns
- Each handler is single-purpose
- Better testability with mocking

## Complete Example: Request Flow

**Request**: `POST /users` with `{"name": "Jane Doe", "email": "jane@example.com"}`

**Flow**:

1. **API Layer** receives request:
   - FastAPI validates JSON against `CreateUserCommand` schema (snake_case → camelCase)
   - Creates handler with injected repository dependency
   - Calls `handler.handle(command)`

2. **Handler Layer** processes:
   - Maps `CreateUserCommand` → `User` domain model
   - Generates `user_id`
   - Maps `User` → Cosmos document `dict`
   - Calls `repository.create(user_doc)`
   - Catches `CosmosAccessConditionFailedError` for duplicate email
   - Maps saved document → `UserResponse`
   - Returns `UserResponse`

3. **Repository Layer** executes:
   - Executes `container.create_item(body=user_doc)`
   - Handles Cosmos DB exceptions
   - Returns created document `dict`

4. **API Layer** responds:
   - FastAPI serializes `UserResponse` → JSON (snake_case → camelCase)
   - Returns `201 Created` with response body

**Responsibilities by Layer**:
- **API**: HTTP validation, status codes, error responses, dependency injection
- **Handler**: Business logic, all mapping (DTO/model/document), orchestration, logging
- **Repository**: Cosmos DB operations, connection management, retry logic

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
    assert response.email == "jane@example.com"
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

## See Also

- [ARCHITECTURE_REFACTORING_SUMMARY.md](../../apps/common-py/ARCHITECTURE_REFACTORING_SUMMARY.md) - Complete migration guide
- [QUICK_START_NEW_ARCHITECTURE.md](../../apps/common-py/QUICK_START_NEW_ARCHITECTURE.md) - Quick reference and examples
- [constitution-python.md](constitution-python.md) - Python backend constitution

---

**Version**: 1.0  
**Created**: 2025-01-13  
**Status**: CURRENT (enforced for all new code)
