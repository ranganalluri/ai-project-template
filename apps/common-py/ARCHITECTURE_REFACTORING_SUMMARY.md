"""
ARCHITECTURE REFACTORING SUMMARY
================================

## Overview
Reorganized the application to follow clean architecture principles with proper layering:

**API Layer → Use Case Layer (Handlers) → Infrastructure Layer (Repository)**

## Changes Made

### 1. Created Infrastructure/Repository Layer

**Location**: `apps/common-py/src/common/infra/repositories/`

**Files Created**:
- `user_repository.py` - UserRepository class for Cosmos DB data access
- `__init__.py` - Exports UserRepository

**Responsibilities**:
- Direct Cosmos DB operations (CRUD)
- Connection management
- Database-level error handling
- Returns domain models (User) or raw documents

**Methods**:
```python
class UserRepository:
    def __init__(cosmos_endpoint, cosmos_key, database_name, container_name, use_managed_identity)
    def create(user_doc: dict) -> dict
    def get_by_id(user_id: str) -> dict | None
    def list_all(offset: int, limit: int) -> tuple[list[dict], int]
    def update(user_id: str, user_doc: dict) -> dict | None
    def delete(user_id: str) -> bool
    def search_by_name(search_term: str, offset: int, limit: int) -> tuple[list[dict], int]
```

### 2. Updated Use Case Layer (Handlers)

**Location**: `apps/common-py/src/common/use_cases/user/`

**Command Handlers** (Write Operations):
- `commands/create_user_handler.py` - CreateUserHandler
- `commands/update_user_handler.py` - UpdateUserHandler
- `commands/delete_user_handler.py` - DeleteUserHandler

**Query Handlers** (Read Operations):
- `queries/get_user_handler.py` - GetUserHandler
- `queries/get_users_handler.py` - GetUsersHandler (renamed from ListUsers)
- `queries/search_users_handler.py` - SearchUsersHandler

**Handler Responsibilities** (NEW):
- ✅ Accept and validate DTOs (Commands/Queries)
- ✅ **Map DTOs ↔ Domain Models** (mapping moved to handlers)
- ✅ **Map Domain Models ↔ Database Documents** (mapping moved to handlers)
- ✅ Call repository for data access
- ✅ Business logic and orchestration
- ✅ Comprehensive logging
- ✅ Error handling and transformation

**Key Change**: Handlers now contain ALL mapping logic (previously in UserMapper utility).

### 3. Mapping Logic Changes

**Before**:
- Mapping in separate `utils/user_mapper.py` utility class
- Handlers imported UserMapper
- Service layer used UserMapper

**After**:
- Mapping logic embedded directly in handlers
- Each handler responsible for its own transformations
- No external mapper dependency

**Mapping Examples in Handlers**:

```python
# Command → Domain Model
user = User(
    user_id=f"user-{uuid4()}",
    name=command.name,
    email=command.email,
)

# Domain Model → Cosmos Document
user_doc = {
    "id": user.user_id,
    "user_id": user.user_id,
    **user.model_dump(),
}

# Domain Model → Response DTO
response = UserResponse(
    user_id=user.user_id,
    name=user.name,
    email=user.email,
)

# Document → Domain Model
user = User(
    user_id=doc["user_id"],
    name=doc["name"],
    email=doc["email"],
)
```

### 4. Architecture Flow

**Old Flow**:
```
API → UserService → UserMapper → Cosmos DB Container
```

**New Flow**:
```
API → Handler (Use Case) → UserRepository → Cosmos DB
     ↓ (mapping)           ↓ (data access)
    DTOs ↔ Domain Models ↔ Documents
```

### 5. Dependency Injection Changes

**Old Pattern** (in API):
```python
def get_user_service(settings: Settings) -> CosmosUserService:
    return CosmosUserService(
        cosmos_endpoint=settings.azure_cosmosdb_endpoint,
        cosmos_key=settings.azure_cosmosdb_key,
        ...
    )

@router.post("/users")
async def add_user(user: User, service: UserService = Depends(get_user_service)):
    return service.create_user(user)
```

**New Pattern** (recommended):
```python
# Step 1: Create repository dependency
def get_user_repository(settings: Settings) -> UserRepository:
    if "user_repository" not in _cache:
        _cache["user_repository"] = UserRepository(
            cosmos_endpoint=settings.azure_cosmosdb_endpoint,
            cosmos_key=settings.azure_cosmosdb_key,
            database_name=settings.database_name,
            container_name=settings.cosmos_users_container,
            use_managed_identity=settings.azure_cosmosdb_key is None,
        )
    return _cache["user_repository"]

# Step 2: Use handlers in routes
@router.post("/users", response_model=UserResponse)
async def create_user(
    command: CreateUserCommand,
    repository: UserRepository = Depends(get_user_repository)
):
    handler = CreateUserHandler(repository)
    return handler.handle(command)

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    repository: UserRepository = Depends(get_user_repository)
):
    handler = GetUserHandler(repository)
    query = GetUserQuery(user_id=user_id)
    response = handler.handle(query)
    if not response:
        raise HTTPException(status_code=404, detail="User not found")
    return response

@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    repository: UserRepository = Depends(get_user_repository)
):
    handler = GetUsersHandler(repository)
    query = ListUsersQuery(page=page, page_size=page_size)
    return handler.handle(query)
```

## Files to Update in API Layer

### 1. Update `apps/api/src/api/services/__init__.py`

Replace `get_user_service()` with `get_user_repository()`:

```python
from common.infra.repositories import UserRepository

def get_user_repository(settings: Settings = Depends(get_settings)) -> UserRepository:
    """Get user repository instance."""
    if "user_repository" not in _services_cache:
        if not settings.azure_cosmosdb_endpoint:
            raise ValueError("AZURE_COSMOSDB_ENDPOINT is required")

        use_managed_identity = settings.azure_cosmosdb_key is None

        _services_cache["user_repository"] = UserRepository(
            cosmos_endpoint=settings.azure_cosmosdb_endpoint,
            cosmos_key=settings.azure_cosmosdb_key,
            database_name=settings.database_name,
            container_name=settings.cosmos_users_container,
            use_managed_identity=use_managed_identity,
        )
        logger.info("Initialized UserRepository")

    return _services_cache["user_repository"]
```

### 2. Update `apps/api/src/api/routes/user.py`

Replace service calls with handler calls:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from api.services import get_user_repository
from common.infra.repositories import UserRepository
from common.use_cases.user.commands import (
    CreateUserCommand, CreateUserHandler,
    UpdateUserHandler, DeleteUserHandler
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
    handler = CreateUserHandler(repository)
    return handler.handle(command)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    repository: UserRepository = Depends(get_user_repository)
):
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
    handler = GetUsersHandler(repository)
    query = ListUsersQuery(page=page, page_size=page_size)
    return handler.handle(query)

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    command: UpdateUserCommand,
    repository: UserRepository = Depends(get_user_repository)
):
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
    handler = DeleteUserHandler(repository)
    success = handler.handle(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
```

### 3. Update Tool Registry (if using search_users)

Update `apps/api/src/api/services/tool_registry.py` to use SearchUsersHandler:

```python
from common.infra.repositories import UserRepository
from common.use_cases.user.queries import SearchUsersQuery, SearchUsersHandler

class ToolRegistry:
    def __init__(self, user_repository: UserRepository | None = None):
        self.user_repository = user_repository
        # ... rest of init

    def search_users(self, name: str, page: int = 1, page_size: int = 10):
        if self.user_repository:
            handler = SearchUsersHandler(self.user_repository)
            query = SearchUsersQuery(name=name, page=page, page_size=page_size)
            response = handler.handle(query)
            return response.model_dump()
        else:
            # Dummy implementation
            return {"users": [], "total": 0}
```

## Benefits of New Architecture

1. **Clear Separation of Concerns**:
   - Repository: Data access only
   - Handlers: Business logic + mapping
   - API: HTTP concerns only

2. **Better Testability**:
   - Can mock repository in handler tests
   - Can test handlers without Cosmos DB
   - Can test API routes without database

3. **Single Responsibility**:
   - Each handler does one operation
   - Mapping logic co-located with handler
   - Repository is pure data access

4. **Easier to Extend**:
   - Add new handlers without changing repository
   - Add new repositories without changing handlers
   - Easy to add caching, logging, metrics

5. **Type Safety**:
   - Handlers work with DTOs (Commands/Queries/Responses)
   - Repository works with documents (dict)
   - Clear boundaries between layers

## Migration Checklist

- [x] Create UserRepository in infra/repositories/
- [x] Update all handlers to include mapping logic
- [x] Update handlers to call repository instead of container
- [x] Remove UserMapper dependency from handlers
- [ ] Update API services/__init__.py to provide UserRepository
- [ ] Update API routes/user.py to use handlers
- [ ] Update tool_registry.py if using search_users
- [ ] Remove or deprecate services/user_service.py
- [ ] Remove utils/user_mapper.py (mapping now in handlers)
- [ ] Update tests to use repository and handlers
- [ ] Update documentation

## Files Status

### ✅ Created/Updated (Common-py)
- `infra/repositories/user_repository.py` - NEW
- `infra/repositories/__init__.py` - NEW
- `use_cases/user/commands/create_user_handler.py` - UPDATED (mapping + repository)
- `use_cases/user/commands/update_user_handler.py` - NEW
- `use_cases/user/commands/delete_user_handler.py` - NEW
- `use_cases/user/queries/get_user_handler.py` - NEW
- `use_cases/user/queries/get_users_handler.py` - UPDATED (mapping + repository)
- `use_cases/user/queries/search_users_handler.py` - NEW
- `use_cases/user/commands/__init__.py` - UPDATED (exports)
- `use_cases/user/queries/__init__.py` - UPDATED (exports)
- `use_cases/user/handlers.py` - UPDATED (convenience exports)

### ⏳ To Be Updated (API)
- `api/src/api/services/__init__.py` - Replace user_service with user_repository
- `api/src/api/routes/user.py` - Use handlers instead of service
- `api/src/api/services/tool_registry.py` - Use SearchUsersHandler

### 🗑️ To Be Deprecated
- `services/user_service.py` - Replace with repository + handlers
- `utils/user_mapper.py` - Mapping logic moved to handlers

## Example: Complete Request Flow

**Request**: `POST /users` with `{"name": "Jane Doe", "email": "jane@example.com"}`

**Flow**:
1. FastAPI receives request → validates JSON against CreateUserCommand schema
2. API route creates CreateUserHandler(repository)
3. Handler.handle(command):
   - Maps CreateUserCommand → User domain model
   - Generates user_id
   - Maps User → Cosmos document dict
   - Calls repository.create(user_doc)
4. Repository.create():
   - Executes Cosmos DB create_item()
   - Returns created document
   - Handles CosmosAccessConditionFailedError
5. Handler maps returned document → UserResponse
6. FastAPI serializes UserResponse → JSON
7. Returns `201 Created` with user data

**Responsibilities by Layer**:
- **API**: HTTP validation, status codes, error responses
- **Handler**: Business logic, DTO/model/document mapping, orchestration
- **Repository**: Cosmos DB operations, connection management
