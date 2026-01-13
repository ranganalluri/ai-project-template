# Python Backend Constitution

**Reference**: See `constitution.md` for core principles  
**Last Updated**: 2025-01-13  
**Scope**: All Python services (`apps/api/`, `apps/common-py/`, `apps/functions/`, `apps/mcp/`)

## Overview

The Python backend comprises four interconnected services:

| Service | Purpose | Technology | Deployment |
|---------|---------|-----------|-----------|
| **API** | REST endpoints + business logic | FastAPI 0.104+ | Azure Container Apps |
| **Common-py** | Shared DTOs, models, services | Pydantic, uv workspace | Workspace member |
| **Functions** | Async background processing | Azure Functions | Azure Container Apps |
| **MCP** | Model Context Protocol server | Python 3.12+ | Azure Container Apps (optional) |

All managed via **uv workspace** with shared dependencies and consistent coding standards.

## Naming Conventions (Mandatory Across All Python Services)

### File & Module Naming
- **Python files**: `snake_case.py`
  - Example: `user_service.py`, `document_mapper.py`, `validation.py`
- **Packages**: `snake_case` directory
  - Example: `common/`, `services/`, `dtos/`
- **Private modules**: `_snake_case.py`
  - Example: `_internal_utils.py`, `_cosmos_client.py`

### Class & Type Naming
- **Classes**: `PascalCase`
  - Example: `UserResponse`, `CreateUserCommand`, `UserMapper`
- **Data Classes/Models**: `PascalCase`
  - Example: `User`, `Document`, `Agent`
- **Exceptions**: `PascalCase` with `Error` or `Exception` suffix
  - Example: `ValidationError`, `NotFoundError`, `AuthenticationException`
- **Enums**: `PascalCase`
  - Example: `AccountStatus`, `DocumentType`

### Function & Method Naming
- **Functions/Methods**: `snake_case`
  - Example: `create_user()`, `validate_email()`, `to_response()`
- **Private functions**: `_snake_case`
  - Example: `_internal_helper()`, `_parse_timestamp()`
- **Async functions**: prefix with `async def` (same naming)
  - Example: `async def get_user()`, `async def process_document()`

### Variable & Constant Naming
- **Variables**: `snake_case`
  - Example: `user_id`, `first_name`, `created_at`, `has_next_page`
- **Constants**: `UPPER_SNAKE_CASE`
  - Example: `MAX_PAGE_SIZE = 100`, `API_VERSION = "v1"`
- **Boolean variables**: prefix with `is_`, `has_`, `can_`
  - Example: `is_active`, `has_next_page`, `can_delete`

### DTO Field Naming
- **Python fields**: `snake_case`
  - Example: `user_id`, `first_name`, `email_address`, `created_at`
- **JSON serialization**: `camelCase` (automatic via Pydantic)
  - Example: `userId`, `firstName`, `emailAddress`, `createdAt`

```python
# ✅ Correct: Python fields in snake_case, auto-converts to camelCase
class UserResponse(BaseResponse):
    user_id: str              # Python: snake_case
    first_name: str
    email_address: str
    created_at: datetime
    # JSON: {"userId": "...", "firstName": "...", "emailAddress": "...", "createdAt": "..."}

# ❌ Wrong: camelCase in Python code
class UserResponse(BaseResponse):
    userId: str               # ❌ Don't use camelCase in Python
    firstName: str
    emailAddress: str
```

## Shared DTO Architecture (Non-Negotiable)

All Python services share DTOs from `apps/common-py/dtos/`:

### Base DTO Classes
```python
# common/dtos/base.py
from pydantic import BaseModel, ConfigDict

def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])

class BaseDTO(BaseModel):
    """Base for all DTOs with automatic naming convention enforcement."""
    model_config = ConfigDict(
        alias_generator=to_camel,      # snake_case → camelCase
        populate_by_name=True,         # Accept both formats
        extra="forbid",                # Reject unexpected fields
        validate_assignment=True,      # Validate on assignment
        use_enum_values=True           # Use enum values
    )

class BaseCommand(BaseDTO):
    """Write operation (Create, Update, Delete)."""
    pass

class BaseQuery(BaseDTO):
    """Read operation request."""
    pass

class BaseResponse(BaseDTO):
    """API response."""
    pass
```

### Command Pattern (Write Operations)
```python
# File: common/use_cases/user/commands/create_user.py
from common.dtos.base import BaseCommand
from pydantic import EmailStr, field_validator

class CreateUserCommand(BaseCommand):
    """Create new user - fields in snake_case, JSON in camelCase."""
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

class UpdateUserCommand(BaseCommand):
    """Update user - all fields optional."""
    user_id: str
    first_name: str | None = None
    last_name: str | None = None
    email_address: str | None = None
```

### Query Pattern (Read Operations)
```python
from common.dtos.base import BaseQuery, BaseResponse
from datetime import datetime

class GetUserQuery(BaseQuery):
    """Get user by ID."""
    user_id: str

class UserResponse(BaseResponse):
    """User response."""
    user_id: str
    first_name: str
    last_name: str
    email_address: str
    account_status: str
    created_at: datetime
    updated_at: datetime

class UserListResponse(BaseResponse):
    """Paginated user list."""
    users: list[UserResponse]
    total_count: int
    has_next_page: bool
    has_previous_page: bool
```

## API Service (apps/api/)

### Service Definition
REST API backend providing unified endpoints for UI and Functions:
- **Technology**: FastAPI 0.104+, Python 3.12+
- **Database**: Azure Cosmos DB (NoSQL)
- **Authentication**: Azure Entra ID (OAuth 2.0 / OIDC)
- **Documentation**: OpenAPI/Swagger (auto-generated)

### Project Structure
```
apps/api/
├── src/
│   └── api/
│       ├── main.py              # FastAPI app entrypoint
│       ├── config.py            # Configuration management
│       ├── middleware.py        # CORS, auth, logging
│       ├── dependencies.py      # Dependency injection
│       ├── routes/              # API route handlers
│       │   ├── users.py
│       │   ├── documents.py
│       │   └── agents.py
│       ├── models/              # Domain models (internal)
│       │   ├── user.py
│       │   ├── document.py
│       │   └── agent.py
│       ├── services/            # Business logic
│       │   ├── user_service.py
│       │   ├── document_service.py
│       │   └── agent_service.py
│       ├── repositories/        # Data access (Cosmos DB)
│       │   ├── user_repository.py
│       │   └── document_repository.py
│       └── mappers/             # DTO ↔ Model conversions
│           └── user_mapper.py
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   ├── integration/
│   └── fixtures/
├── Dockerfile
└── pyproject.toml
```

### Route Pattern (FastAPI)
```python
# apps/api/src/api/routes/users.py
from fastapi import APIRouter, HTTPException, Query
from common.dtos.commands import CreateUserCommand, UpdateUserCommand
from common.dtos.queries import UserResponse, UserListResponse
from ..services.user_service import UserService

router = APIRouter(prefix="/api/users", tags=["users"])
service = UserService()

@router.post("", response_model=UserResponse, status_code=201)
async def create_user(command: CreateUserCommand) -> UserResponse:
    """Create a new user.
    
    Request (camelCase):
    {"firstName": "Jane", "lastName": "Doe", "emailAddress": "jane@example.com"}
    
    Response (camelCase):
    {"userId": "...", "firstName": "Jane", ...}
    """
    try:
        return await service.create_user(command)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str) -> UserResponse:
    """Get user by ID."""
    try:
        from common.dtos.queries import GetUserQuery
        return await service.get_user(GetUserQuery(user_id=user_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
) -> UserListResponse:
    """List users with pagination."""
    from common.dtos.queries import ListUsersQuery
    return await service.list_users(
        ListUsersQuery(page=page, page_size=page_size)
    )
```

### Service Pattern
```python
# apps/api/src/api/services/user_service.py
from common.dtos.commands import CreateUserCommand, UpdateUserCommand
from common.dtos.queries import GetUserQuery, UserResponse, UserListResponse
from ..mappers.user_mapper import UserMapper
from ..repositories.user_repository import UserRepository

class UserService:
    """Business logic orchestration."""
    
    def __init__(self, repository: UserRepository = None):
        self.repository = repository or UserRepository()
    
    async def create_user(self, command: CreateUserCommand) -> UserResponse:
        """Accept Command, return Response."""
        user = UserMapper.from_create_command(command)
        saved_user = await self.repository.create(user)
        return UserMapper.to_response(saved_user)
    
    async def get_user(self, query: GetUserQuery) -> UserResponse:
        """Accept Query, return Response."""
        user = await self.repository.get_by_id(query.user_id)
        if not user:
            raise ValueError(f"User not found: {query.user_id}")
        return UserMapper.to_response(user)
```

## Common-py Shared Library (apps/common-py/)

### Purpose
Centralized utilities used by API, Functions, and MCP:
- DTO definitions (Commands, Queries, Responses)
- Domain models (User, Document, Agent)
- Mappers (DTO ↔ Model ↔ Cosmos DB)
- Services (business logic)
- Repositories (data access)
- Validators and utilities

### Structure
```
apps/common-py/
├── src/common/
│   ├── dtos/                  # Base DTO classes only
│   │   ├── base.py            # BaseDTO, BaseCommand, BaseQuery, BaseResponse
│   │   └── __init__.py
│   ├── use_cases/             # Commands & Queries organized by entity
│   │   ├── user/
│   │   │   ├── commands/      # Write operations (Create, Update, Delete)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── create_user.py
│   │   │   │   ├── update_user.py
│   │   │   │   └── delete_user.py
│   │   │   ├── queries/       # Read operations (Get, List, Search)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── get_user.py
│   │   │   │   ├── list_users.py
│   │   │   │   └── search_users.py
│   │   │   └── __init__.py
│   │   ├── document/          # Document use cases
│   │   │   ├── commands/
│   │   │   └── queries/
│   │   └── agent/             # Agent use cases
│   │       ├── commands/
│   │       └── queries/
│   ├── models/                # Domain models (User, Document, Agent)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── document.py
│   │   └── agent.py
│   ├── services/              # Business logic
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   ├── document_service.py
│   │   └── agent_service.py
│   ├── repositories/          # Data access (Cosmos DB)
│   │   ├── __init__.py
│   │   ├── user_repository.py
│   │   └── document_repository.py
│   ├── mappers/               # DTO ↔ Model conversions
│   │   ├── __init__.py
│   │   └── user_mapper.py
│   └── utils/                 # Shared utilities
│       ├── __init__.py
│       ├── formatting.py
│       ├── validation.py
│       └── constants.py
├── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_dto_naming_conventions.py
│       ├── services/
│       │   └── test_user_service.py
│       ├── use_cases/
│       │   └── user/
│       │       ├── test_create_user.py
│       │       └── test_get_user.py
│       └── utils/
│           └── test_validation.py
├── pyproject.toml
├── NAMING_CONVENTIONS.md
├── USER_SERVICE_ARCHITECTURE.md
└── README.md
```

#### Imports from Use Cases
```python
# Import commands from use_cases
from common.use_cases.user.commands.create_user import CreateUserCommand
from common.use_cases.user.commands.update_user import UpdateUserCommand
from common.use_cases.user.commands.delete_user import DeleteUserCommand

# Import queries and responses from use_cases
from common.use_cases.user.queries.get_user import GetUserQuery, UserResponse
from common.use_cases.user.queries.list_users import ListUsersQuery, UserListResponse

# Import base DTOs from dtos (shared across all use cases)
from common.dtos.base import BaseDTO, BaseCommand, BaseQuery, BaseResponse
```
**Never expose domain models directly in APIs**. Always use DTOs:

```python
# ✅ Correct: Convert via mapper
user = repository.get_user(user_id)
return UserMapper.to_response(user)  # Returns UserResponse DTO

# ❌ Wrong: Direct model exposure
return user  # Returns internal User model
```

## Functions Service (apps/functions/)

### Service Definition
Asynchronous background processing for long-running tasks:
- **Technology**: Azure Functions, Python 3.12+, containerized
- **Messaging**: Azure Service Bus (triggers)
- **Storage**: Azure Blob Storage (documents)
- **Logging**: Application Insights

### Service Bus Trigger Pattern
```python
# apps/functions/functions/process_document.py
import azure.functions as func
import json
from common.services.document_service import DocumentService

def process_document_trigger(msg: func.ServiceBusMessage) -> None:
    """Process document from Service Bus queue.
    
    Message body (camelCase JSON from API):
    {
        "documentId": "doc-123",
        "storageUri": "https://storage.blob.core.windows.net/uploads/doc-123.pdf",
        "userId": "user-456"
    }
    """
    try:
        # Parse message (camelCase from API)
        message_json = json.loads(msg.get_body().decode())
        document_id = message_json.get("documentId")
        storage_uri = message_json.get("storageUri")
        
        # Process using common service (uses snake_case internally)
        service = DocumentService()
        result = service.process_document(
            document_id=document_id,
            storage_uri=storage_uri
        )
        
        # Log success
        func.logging.info(
            f"Processed document: {document_id}",
            extra={"document_id": document_id}
        )
    except Exception as e:
        func.logging.error(f"Error: {str(e)}")
        raise

# Register function
app = func.FunctionApp()
service_bus_trigger = func.ServiceBusQueueTrigger(
    arg_name="msg",
    queue_name="document-processing",
    connection="SERVICE_BUS_CONNECTION_STRING"
)
app.register_functions(
    func.AsynchronousFunction(process_document_trigger, service_bus_trigger)
)
```

### Timer Trigger Pattern
```python
# apps/functions/functions/cleanup_old_uploads.py
import azure.functions as func
from datetime import datetime, timedelta
from common.services.cleanup_service import CleanupService

def cleanup_old_uploads(timer: func.TimerRequest) -> None:
    """Cleanup old uploads daily (UTC cron: 0 0 * * * = midnight).
    
    Scheduled task - runs on timer, not triggered by message.
    Uses snake_case internally for all variables and function calls.
    """
    try:
        service = CleanupService()
        deleted_count = service.cleanup_uploads(hours_old=24)
        
        func.logging.info(f"Deleted {deleted_count} old uploads")
    except Exception as e:
        func.logging.error(f"Cleanup failed: {str(e)}")
        raise
```

## MCP Service (apps/mcp/) - Optional

### Service Definition
Model Context Protocol server for AI tool integration (optional):
- **Technology**: Python 3.12+, MCP protocol
- **Purpose**: Expose project capabilities to Claude/other AI models
- **Example**: Read documentation, list resources, execute operations

### Basic Pattern
```python
# apps/mcp/src/server.py
import mcp
from common.services.user_service import UserService

class ProjectServer:
    """MCP server for AI tool integration."""
    
    async def handle_list_resources(self):
        """List available resources."""
        return {
            "resources": [
                {"name": "users", "description": "User management"},
                {"name": "documents", "description": "Document processing"},
                {"name": "agents", "description": "AI agents"}
            ]
        }
    
    async def handle_call_tool(self, tool_name: str, arguments: dict):
        """Execute a tool."""
        if tool_name == "list_users":
            service = UserService()
            return await service.list_users()
        # ... handle other tools
```

## Testing (All Python Services)

### Unit Tests
```bash
# Run tests with coverage
cd apps/api && uv run pytest --cov=src --cov-fail-under=70

# Run specific test file
uv run pytest tests/test_user_service.py -v

# Run with markers
uv run pytest -m asyncio tests/
```

### Test Pattern
```python
# tests/test_user_service.py
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
async def test_get_user_not_found():
    """Test error handling for missing user."""
    service = UserService()
    
    with pytest.raises(ValueError, match="User not found"):
        from common.dtos.queries import GetUserQuery
        await service.get_user(GetUserQuery(user_id="invalid-id"))
```

## Configuration Management

### Environment Variables
```bash
# .env (all Python services)
PYTHONPATH=.

# Cosmos DB
COSMOS_DB_ENDPOINT=https://your-cosmos.documents.azure.com:443/
COSMOS_DB_KEY=your-primary-key
COSMOS_DB_DATABASE=ai_project

# Azure Entra ID
AZURE_ENTRA_TENANT_ID=your-tenant-id
AZURE_ENTRA_CLIENT_ID=your-client-id
AZURE_ENTRA_CLIENT_SECRET=your-secret

# Service Bus
SERVICE_BUS_CONNECTION_STRING=Endpoint=sb://your-namespace.servicebus.windows.net/

# Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...

# API
FASTAPI_ENV=development
FASTAPI_DEBUG=true
API_PORT=8000

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Config Class
```python
# apps/api/src/api/config.py
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    """Application configuration from environment variables."""
    
    fastapi_env: str = "development"
    fastapi_debug: bool = False
    api_port: int = 8000
    
    cosmos_db_endpoint: str
    cosmos_db_key: str
    cosmos_db_database: str = "ai_project"
    
    azure_entra_tenant_id: str
    azure_entra_client_id: str
    azure_entra_client_secret: str
    
    service_bus_connection_string: str
    
    cors_origins: list[str] = ["http://localhost:5173"]
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## Development Commands

### Workspace Management
```bash
# Install all Python dependencies
uv sync

# Update lock file
uv lock

# Show dependency tree
uv pip tree
```

### API Service
```bash
# Run API locally
cd apps/api && uv run uvicorn src.api.main:app --reload --port 8000

# Run tests
cd apps/api && uv run pytest

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/
uv run ruff format src/
```

### Functions Service
```bash
# Run functions locally
cd apps/functions && uv run func start

# Run tests
cd apps/functions && uv run pytest
```

### Common-py Library
```bash
# Run tests
cd apps/common-py && uv run pytest --cov=src --cov-fail-under=70

# Run naming convention tests
uv run pytest tests/test_dto_naming_conventions.py -v
```

### Docker
```bash
# Build API image
docker build -f apps/api/Dockerfile -t ai-api:latest .

# Build Functions image
docker build -f apps/functions/Dockerfile -t ai-functions:latest .

# Run with Docker Compose (emulators)
docker-compose up -d
```

## Deployment

### Container Requirements
- Multi-stage Dockerfile with production optimization
- Health check endpoint: `GET /health` → `{"status": "ok"}`
- Graceful shutdown handling (SIGTERM)
- All config from environment variables (no hardcoded values)
- Secrets from Azure Key Vault

### Azure Deployment
```bash
# Full provisioning + deployment
azd up

# Redeploy after code changes
azd deploy

# View logs and metrics
azd monitor --logs
```

## Resources

- **Naming Conventions**: [apps/common-py/NAMING_CONVENTIONS.md](../../../../apps/common-py/NAMING_CONVENTIONS.md)
- **Architecture Guide**: [apps/common-py/USER_SERVICE_ARCHITECTURE.md](../../../../apps/common-py/USER_SERVICE_ARCHITECTURE.md)
- **Test Examples**: [apps/common-py/tests/test_dto_naming_conventions.py](../../../../apps/common-py/tests/test_dto_naming_conventions.py)
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Pydantic Docs**: https://docs.pydantic.dev/
- **Azure Functions**: https://learn.microsoft.com/en-us/azure/azure-functions/

---

**Version**: 1.0  
**Created**: 2025-01-13  
**Parent**: [constitution.md](constitution.md)  
**Covers**: API, Common-py, Functions, MCP services
