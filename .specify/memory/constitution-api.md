# API Service Constitution

**Reference**: See `constitution.md` for core principles  
**Last Updated**: 2025-01-13  
**Scope**: `apps/api/` (FastAPI backend service)

## Service Definition

The API service provides a **unified, secure REST interface** for all frontend and backend consumers:
- **Technology**: FastAPI 0.104+, Python 3.12+
- **Deployment**: Azure Container Apps (containerized)
- **Database**: Azure Cosmos DB (NoSQL)
- **Authentication**: Azure Entra ID (OAuth 2.0 / OIDC)
- **Documentation**: OpenAPI/Swagger (auto-generated from Pydantic models)

## API Design Principles

### I. Single Unified Endpoint (Non-Negotiable)
- All routes MUST be under `/api/*` prefix
- Coherent structure: `/api/agents/*`, `/api/documents/*`, `/api/users/*`, etc.
- Version prefix optional but recommended: `/api/v1/*`
- CORS enabled with specific origin allowlist (production-hardened)

### II. DTO Architecture (Required)
All endpoints MUST use DTOs with CQRS-inspired pattern:

**Structure**:
```
apps/common-py/src/common/
├── dtos/                      # Base DTO classes only
│   ├── base.py                # BaseDTO, BaseCommand, BaseQuery, BaseResponse
│   └── __init__.py
└── use_cases/                 # Commands & Queries organized by entity
    ├── user/
    │   ├── commands/          # Write operations (Create, Update, Delete)
    │   │   ├── __init__.py
    │   │   ├── create_user.py
    │   │   ├── update_user.py
    │   │   └── delete_user.py
    │   ├── queries/           # Read operations (Get, List, Search)
    │   │   ├── __init__.py
    │   │   ├── get_user.py
    │   │   ├── list_users.py
    │   │   ├── search_users.py
    │   │   └── responses.py
    │   └── __init__.py
    ├── agent/
    │   ├── commands/
    │   └── queries/
    └── document/
        ├── commands/
        └── queries/
```

**Naming Conventions**:
- **Python fields**: `snake_case`
- **Class names**: `PascalCase`
- **JSON serialization**: `camelCase` (automatic via alias_generator)
- **Constants**: `UPPER_SNAKE_CASE`

**DTO Rules**:
1. ALL DTOs inherit from `BaseDTO` or one of: `BaseCommand`, `BaseQuery`, `BaseResponse`
2. Base classes enforce `alias_generator=to_camel` for automatic conversion
3. `populate_by_name=True` allows both formats in request body
4. `extra="forbid"` rejects unexpected fields
5. Field validators enforce constraints (email, phone, patterns)
6. Optional fields use `str | None = None` syntax
7. Commands and Queries stored in `common/use_cases/` (organized by entity)
8. Base DTO classes stored in `common/dtos/base.py` (shared across all use cases)

**Command Pattern** (Write Operations):
```python
# File: common/use_cases/user/commands/create_user.py
from common.dtos.base import BaseCommand
from pydantic import EmailStr, field_validator

class CreateUserCommand(BaseCommand):
    """Create new user. Fields in snake_case → JSON camelCase."""
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

**Query Pattern** (Read Operations):
```python
# File: common/use_cases/user/queries/get_user.py
from common.dtos.base import BaseQuery, BaseResponse
from datetime import datetime

class UserResponse(BaseResponse):
    """User response with full details. Fields → camelCase JSON."""
    user_id: str
    first_name: str
    last_name: str
    email_address: str
    phone_number: str | None
    account_status: str
    created_at: datetime
    updated_at: datetime
```

**Pagination Pattern**:
```python
class UserListResponse(BaseResponse):
    """Paginated user list."""
    users: list[UserResponse]
    total_count: int              # → totalCount in JSON
    page_size: int                # → pageSize
    current_page: int             # → currentPage
    total_pages: int              # → totalPages
    has_next_page: bool           # → hasNextPage
    has_previous_page: bool       # → hasPreviousPage
```

### III. Handler Layer (Use Case Layer - Required)
Handlers MUST accept Commands/Queries and return Responses following Clean Architecture:

**Architecture**: API → Use Case Handlers → Repository → Cosmos DB

```python
# File: common/use_cases/user/commands/create_user_handler.py
from common.use_cases.user.commands import CreateUserCommand
from common.use_cases.user.queries import UserResponse
from common.infra.repositories import UserRepository
from common.models.user import User

class CreateUserHandler:
    """Handler for CreateUserCommand - accepts Command, returns Response."""
    
    def __init__(self, repository: UserRepository):
        self.repository = repository
    
    def handle(self, command: CreateUserCommand) -> UserResponse:
        """
        Accept Command, map to domain model, save via repository.
        Handler responsibility: DTO ↔ Model mapping
        Repository responsibility: Model ↔ Document mapping
        """
        # Map command to domain model
        user = User(
            user_id=f"user-{uuid4()}",
            name=command.name,
            email=command.email,
        )
        
        # Save via repository (repository handles document conversion)
        created_user = self.repository.create(user)
        
        # Map to response DTO
        return UserResponse(
            user_id=created_user.user_id,
            name=created_user.name,
            email=created_user.email,
        )
```

**Query Handler Example**:
```python
# File: common/use_cases/user/queries/get_users_handler.py
from common.use_cases.user.queries import ListUsersQuery, UserListResponse, UserResponse
from common.infra.repositories import UserRepository

class GetUsersHandler:
    """Handler for ListUsersQuery - accepts Query, returns paginated Response."""
    
    def __init__(self, repository: UserRepository):
        self.repository = repository
    
    def handle(self, query: ListUsersQuery) -> UserListResponse:
        """Accept Query with pagination, return paginated Response."""
        offset = (query.page - 1) * query.page_size
        
        # Get users from repository (returns User models)
        users, total = self.repository.list_all(offset=offset, limit=query.page_size)
        
        # Map to response DTOs
        user_responses = [
            UserResponse(
                user_id=user.user_id,
                name=user.name,
                email=user.email,
            )
            for user in users
        ]
        
        return UserListResponse(
            users=user_responses,
            total=total,
            page=query.page,
            page_size=query.page_size,
            total_pages=(total + query.page_size - 1) // query.page_size,
        )
```

### IV. Repository Layer (Infrastructure - Required)
Repositories MUST inherit from BaseRepository[T] and return domain models:

```python
# File: common/infra/repositories/user_repository.py
from common.infra.repositories.base_repository import BaseRepository
from common.models.user import User

class UserRepository(BaseRepository[User]):
    """Repository for user data access with Cosmos DB.
    
    Responsibilities:
    - Direct Cosmos DB operations (CRUD)
    - Connection management
    - Database-level error handling
    - Map between Cosmos documents and User domain models
    - Returns User domain models (not dicts)
    """
    
    def _to_document(self, user: User) -> dict:
        """Convert User model to Cosmos DB document."""
        return {
            "id": user.user_id,
            "user_id": user.user_id,
            **user.model_dump(),
        }
    
    def _from_document(self, doc: dict) -> User:
        """Convert Cosmos DB document to User model."""
        return User(
            user_id=doc["user_id"],
            name=doc["name"],
            email=doc["email"],
        )
    
    def create(self, user: User) -> User:
        """Create a new user - returns User model."""
        user_doc = self._to_document(user)
        created_doc = self.container.create_item(body=user_doc)
        return self._from_document(created_doc)
    
    def list_all(self, offset: int = 0, limit: int = 10) -> tuple[list[User], int]:
        """List all users with pagination - returns User models."""
        # Get paginated results
        sql_query = f"SELECT * FROM c OFFSET {offset} LIMIT {limit}"
        items = list(self.container.query_items(query=sql_query))
        
        users = [self._from_document(doc) for doc in items]
        return users, total
```

### V. FastAPI Routes (Required)
Routes MUST define request/response models using DTOs and dependency injection for handlers:

```python
from fastapi import APIRouter, HTTPException, Depends
from common.use_cases.user.commands import CreateUserCommand, CreateUserHandler
from common.use_cases.user.queries import (
    GetUsersHandler,
    ListUsersQuery,
    UserListResponse,
    UserResponse,
)
from api.dependencies import get_create_user_handler, get_get_users_handler

router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    command: CreateUserCommand,
    handler: CreateUserHandler = Depends(get_create_user_handler),
) -> UserResponse:
    """
    Create a new user.
    
    Request (accepts both snake_case and camelCase):
    {
        "name": "Jane Doe",
        "email": "jane@example.com"
    }
    
    Response:
    {
        "userId": "user-uuid-123",
        "name": "Jane Doe",
        "email": "jane@example.com"
    }
    """
    try:
        return handler.handle(command)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    handler: GetUsersHandler = Depends(get_get_users_handler),
) -> UserListResponse:
    """List users with pagination."""
    query = ListUsersQuery(page=page, page_size=page_size)
    return handler.handle(query)
```

### VI. Dependency Injection (Required)
Handler dependencies MUST be defined in `api/dependencies.py`:

```python
# File: apps/api/src/api/dependencies.py
from api.config import get_settings
from common.infra.repositories import UserRepository
from common.use_cases.user.commands.create_user_handler import CreateUserHandler
from common.use_cases.user.queries.get_users_handler import GetUsersHandler

def get_user_repository() -> UserRepository:
    """Get user repository instance."""
    settings = get_settings()
    return UserRepository(
        cosmos_endpoint=settings.azure_cosmosdb_endpoint,
        cosmos_key=settings.azure_cosmosdb_key,
        database_name=settings.database_name,
        container_name="users",
        use_managed_identity=False,
    )

def get_create_user_handler() -> CreateUserHandler:
    """Get CreateUserHandler instance."""
    repository = get_user_repository()
    return CreateUserHandler(repository=repository)

def get_get_users_handler() -> GetUsersHandler:
    """Get GetUsersHandler instance."""
    repository = get_user_repository()
    return GetUsersHandler(repository=repository)
```
```

## Middleware & Security

### Required Middleware (in order)
1. **CORS**: Specific origin allowlist (production hardened)
2. **Authentication**: Azure Entra ID (OAuth 2.0)
3. **Logging**: Structured logging (JSON format) to Application Insights
4. **Request ID**: Unique ID for tracing (X-Request-ID header)
5. **Rate Limiting**: Per-tenant/per-user throttling (Service Bus)
6. **Error Handling**: Consistent error format (structured exceptions)

### Example Middleware
```python
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import uuid
import logging

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={
            "error": str(exc),
            "request_id": request.state.request_id
        }
    )
```

## Testing Requirements

### Unit Tests (Minimum 70% coverage)
```bash
cd apps/api && uv run pytest tests/ --cov=src --cov-fail-under=70
```

**Required test coverage**:
- All route handlers
- All service methods
- All mappers
- All validators
- Error handling paths

### Integration Tests
```bash
uv run pytest tests/integration/ -v
```

**Required coverage**:
- API → Service interactions
- Service → Repository interactions
- Cosmos DB document transformations
- Azure Entra ID authentication flow
- API → Function async messaging

### Example Tests
```python
import pytest
from common.dtos.commands import CreateUserCommand
from src.api.services.user_service import UserService

@pytest.mark.asyncio
async def test_create_user_with_valid_command():
    """Test service accepts Command and returns Response."""
    service = UserService()
    command = CreateUserCommand(
        first_name="Jane",
        last_name="Doe",
        email_address="jane@example.com"
    )
    response = await service.create_user(command)
    
    assert response.user_id is not None
    assert response.first_name == "Jane"
    assert response.account_status == "active"

@pytest.mark.asyncio
async def test_create_user_rejects_invalid_email():
    """Test validation rejects malformed emails."""
    service = UserService()
    with pytest.raises(ValueError):
        await service.create_user(
            CreateUserCommand(
                first_name="Jane",
                last_name="Doe",
                email_address="invalid-email"
            )
        )
```

## Configuration Management

### Environment Variables
```bash
# .env (local development)
FASTAPI_ENV=development
FASTAPI_DEBUG=true
COSMOS_DB_ENDPOINT=https://localhost:8081
COSMOS_DB_KEY=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqwm57OJjlak1LchZbwXwmarwxwuJF7dvjXg==
AZURE_ENTRA_TENANT_ID=your-tenant-id
AZURE_ENTRA_CLIENT_ID=your-client-id
AZURE_ENTRA_CLIENT_SECRET=your-client-secret
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Configuration Module
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    fastapi_env: str = "development"
    fastapi_debug: bool = False
    cosmos_db_endpoint: str
    cosmos_db_key: str
    cosmos_db_database: str = "ai_project"
    azure_entra_tenant_id: str
    azure_entra_client_id: str
    cors_origins: list[str] = ["http://localhost:5173"]
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## Development Commands

```bash
# Install dependencies
uv sync

# Run API locally with reload
cd apps/api && uv run uvicorn src.api.main:app --reload --port 8000

# Run tests with coverage
cd apps/api && uv run pytest --cov=src --cov-fail-under=70

# Type checking
uv run mypy src/

# Linting & formatting
uv run ruff check src/
uv run ruff format src/

# Build Docker image
docker build -f apps/api/Dockerfile -t ai-api:latest .

# Run API in Docker
docker run -p 8000:8000 \
  -e COSMOS_DB_ENDPOINT=host.docker.internal:8081 \
  ai-api:latest
```

## Deployment

### Container Requirements
- Multi-stage Dockerfile with production optimization
- Health check endpoint: `GET /api/health` (returns `{"status": "ok"}`)
- Graceful shutdown (SIGTERM handling)
- All configuration via environment variables (no hardcoded values)
- Secrets from Azure Key Vault (not environment variables)

### Azure Container Apps Deployment
```bash
# Via Azure Developer CLI
azd up        # Full provisioning + deployment
azd deploy    # Redeploy after code changes
azd monitor   # View logs and metrics
```

## Resources

- **Quick Reference**: [apps/common-py/NAMING_CONVENTIONS.md](../../../../apps/common-py/NAMING_CONVENTIONS.md)
- **Full Guide**: [apps/common-py/USER_SERVICE_ARCHITECTURE.md](../../../../apps/common-py/USER_SERVICE_ARCHITECTURE.md)
- **Test Examples**: [apps/common-py/tests/test_dto_naming_conventions.py](../../../../apps/common-py/tests/test_dto_naming_conventions.py)
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Pydantic Docs**: https://docs.pydantic.dev/

---

**Version**: 1.0  
**Created**: 2025-01-13  
**Parent**: [constitution.md](constitution.md)
