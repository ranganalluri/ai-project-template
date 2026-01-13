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

### III. Service Layer (Required)
Services MUST accept Commands/Queries and return Responses:

```python
class UserService:
    """Business logic orchestration with DTOs."""
    
    async def create_user(self, command: CreateUserCommand) -> UserResponse:
        """Accept Command, return Response (NOT internal models)."""
        user = UserMapper.from_create_command(command)
        saved_user = await self.repository.save(user)
        return UserMapper.to_response(saved_user)
    
    async def get_user(self, query: GetUserQuery) -> UserResponse:
        """Accept Query, return Response."""
        user = await self.repository.get_by_id(query.user_id)
        if not user:
            raise ValueError(f"User {query.user_id} not found")
        return UserMapper.to_response(user)
    
    async def list_users(self, query: ListUsersQuery) -> UserListResponse:
        """Accept Query with pagination, return paginated Response."""
        users, total = await self.repository.list(
            skip=(query.page - 1) * query.page_size,
            limit=query.page_size,
            sort_by=query.sort_by
        )
        return UserListResponse(
            users=[UserMapper.to_response(u) for u in users],
            total_count=total,
            page_size=query.page_size,
            current_page=query.page,
            total_pages=(total + query.page_size - 1) // query.page_size,
            has_next_page=query.page * query.page_size < total,
            has_previous_page=query.page > 1
        )
```

### IV. Mapper Layer (Required)
Mappers transform between DTOs, domain models, and Cosmos DB documents:

```python
class UserMapper:
    """Transform between DTOs ↔ Models ↔ Cosmos DB documents."""
    
    @staticmethod
    def to_response(user: User) -> UserResponse:
        """Convert domain model to API response."""
        return UserResponse(
            user_id=user.id,
            first_name=user.name.split()[0],
            last_name=user.name.split()[1] if len(user.name.split()) > 1 else "",
            email_address=user.email,
            phone_number=user.phone,
            account_status=user.status,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    
    @staticmethod
    def from_create_command(cmd: CreateUserCommand) -> User:
        """Convert command to domain model."""
        return User(
            name=f"{cmd.first_name} {cmd.last_name}",
            email=cmd.email_address,
            phone=cmd.phone_number,
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    @staticmethod
    def to_cosmos_document(user: User) -> dict:
        """Convert to Cosmos DB document (with partitionKey)."""
        return {
            "id": user.id,
            "partitionKey": user.tenant_id,  # Required for Cosmos DB
            "type": "user",
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "status": user.status,
            "createdAt": user.created_at.isoformat(),
            "updatedAt": user.updated_at.isoformat()
        }
```

### V. FastAPI Routes (Required)
Routes MUST define request/response models using DTOs:

```python
from fastapi import APIRouter, HTTPException, Query
from common.use_cases.user.commands.create_user import CreateUserCommand
from common.use_cases.user.commands.update_user import UpdateUserCommand
from common.use_cases.user.queries.get_user import GetUserQuery, UserResponse
from common.use_cases.user.queries.list_users import ListUsersQuery, UserListResponse

router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("", response_model=UserResponse, status_code=201)
async def create_user(command: CreateUserCommand) -> UserResponse:
    """
    Create a new user.
    
    Request (camelCase JSON):
    {
        "firstName": "Jane",
        "lastName": "Doe",
        "emailAddress": "jane@example.com",
        "phoneNumber": "+1-555-0123"
    }
    
    Response (camelCase JSON):
    {
        "userId": "user-uuid-123",
        "firstName": "Jane",
        "lastName": "Doe",
        "emailAddress": "jane@example.com",
        "phoneNumber": "+1-555-0123",
        "accountStatus": "active",
        "createdAt": "2025-01-13T10:00:00Z",
        "updatedAt": "2025-01-13T10:00:00Z"
    }
    """
    try:
        return await user_service.create_user(command)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str) -> UserResponse:
    """Get user by ID."""
    try:
        from common.dtos.queries import GetUserQuery
        return await user_service.get_user(GetUserQuery(user_id=user_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    sort_by: str = Query("created_at")
) -> UserListResponse:
    """List users with pagination."""
    from common.dtos.queries import ListUsersQuery
    return await user_service.list_users(
        ListUsersQuery(page=page, page_size=page_size, sort_by=sort_by)
    )
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
