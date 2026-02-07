---
applyTo: "*"
---

# AI Project Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-01-13

## Active Technologies

- **Backend**: Python 3.12+, FastAPI 0.104+, uv package manager
- **Frontend**: Node.js 20+, React 18, TypeScript 5.0+, Vite, Tailwind CSS
- **Shared Libraries**: npm workspaces (ui-lib), uv workspace (common-py)
- **Infrastructure**: Docker, Azure Container Apps, Bicep IaC
- **Databases**: Azure Cosmos DB (NoSQL), Azure Blob Storage
- **AI/ML**: Azure OpenAI, Azure Document Intelligence
- **Messaging**: Azure Service Bus
- **Authentication**: Azure Entra ID (OAuth 2.0/OIDC)
- **Observability**: Application Insights, Azure Monitor

## Project Structure

```text
ai-project-template/
├── apps/
│   ├── ui/              # React frontend (Vite)
│   ├── ui-lib/          # Shared React components
│   ├── api/             # FastAPI backend
│   ├── functions/       # Azure Functions (containerized)
│   ├── common-py/       # Shared Python utilities
│   └── mcp/             # Model Context Protocol
├── infra/               # Bicep infrastructure templates
├── scripts/             # Deployment and setup scripts
├── .specify/            # Project specifications and templates
├── .github/             # Workflows and agent definitions
├── docs/                # Documentation
├── pyproject.toml       # Root Python workspace
├── package.json         # Root npm workspace
└── azure.yaml           # Azure Developer CLI config
```

## Development Commands

### Python (uv workspace)
```bash
# Install dependencies
uv sync

# Run API locally
cd apps/api && uv run uvicorn src.api.main:app --reload --port 8000

# Run Functions locally
cd apps/functions && uv run func start

# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Linting
uv run ruff check .
uv run ruff format .
```

### JavaScript/TypeScript (npm workspaces)
```bash
# Install dependencies
npm ci

# Run UI dev server
npm -w apps/ui run dev

# Build ui-lib
npm -w apps/ui-lib run build

# Run tests
npm test

# Linting
npm run lint
npm run format
```

### Docker & Deployment
```bash
# Local stack with emulators
docker-compose up

# Build specific service image
docker build -f apps/api/Dockerfile -t ai-api:latest .

# Deploy via Azure Developer CLI
azd up
azd deploy

# Deploy specific service
azd deploy api
```

## Code Style

### Naming Conventions (Mandatory)

**Python Fields**: `snake_case`
```python
user_id: str
first_name: str
email_address: str
created_at: datetime
```

**Class Names**: `PascalCase`
```python
UserResponse
CreateUserCommand
UserMapper
```

**JSON/API**: `camelCase` (automatic conversion)
```json
{"userId": "123", "firstName": "Jane", "createdAt": "2025-01-13T10:00:00Z"}
```

**Constants**: `UPPER_SNAKE_CASE`
```python
MAX_PAGE_SIZE = 100
API_VERSION = "v1"
```

### DTO Architecture (Required for All APIs)

**ALL new API endpoints MUST use DTOs with this structure:**

```
apps/common-py/src/common/dtos/
├── base.py              # BaseDTO with alias_generator=to_camel
├── commands/            # Write operations (CreateXCommand, UpdateXCommand)
├── queries/             # Read operations (GetXQuery, XResponse)
└── __init__.py
```

**Required Pattern**:

1. **Base DTO** (already exists in `common/dtos/base.py`):
```python
from pydantic import BaseModel, ConfigDict

def to_camel(string: str) -> str:
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])

class BaseDTO(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,      # Auto-convert snake_case → camelCase
        populate_by_name=True,         # Accept both formats
        extra="forbid"                 # Reject extra fields
    )
```

2. **Commands** (write operations):
```python
from common.dtos.base import BaseCommand

class CreateUserCommand(BaseCommand):
    first_name: str              # Python: snake_case
    last_name: str
    email_address: str
    # JSON automatically uses: firstName, lastName, emailAddress
```

3. **Queries & Responses** (read operations):
```python
from common.dtos.base import BaseQuery, BaseResponse

class GetUserQuery(BaseQuery):
    user_id: str                 # Python: snake_case → JSON: userId

class UserResponse(BaseResponse):
    user_id: str
    first_name: str
    created_at: datetime
    # JSON: {"userId": "...", "firstName": "...", "createdAt": "..."}
```

4. **Mapper** (layer separation):
```python
class UserMapper:
    @staticmethod
    def to_response(user: User) -> UserResponse:
        return UserResponse(user_id=user.id, ...)
    
    @staticmethod
    def from_create_command(cmd: CreateUserCommand) -> User:
        return User(name=f"{cmd.first_name} {cmd.last_name}", ...)
```

5. **Service** (business logic):
```python
class UserService:
    async def create_user(self, command: CreateUserCommand) -> UserResponse:
        user = UserMapper.from_create_command(command)
        saved = await self.repository.save(user)
        return UserMapper.to_response(saved)
```

6. **FastAPI Route**:
```python
@router.post("/users", response_model=UserResponse)
async def create_user(command: CreateUserCommand) -> UserResponse:
    return await user_service.create_user(command)
```

**Key Rules**:
- ✅ Use `snake_case` for Python fields
- ✅ Use `PascalCase` for class names
- ✅ Inherit from `BaseDTO`/`BaseCommand`/`BaseQuery`/`BaseResponse`
- ✅ JSON automatically converts to `camelCase`
- ✅ Add field validators for constraints
- ✅ Use Mappers for transformations
- ✅ Services accept Commands/Queries, return Responses
- ❌ Never expose internal models directly in API
- ❌ Never use `camelCase` in Python code
- ❌ Never bypass DTOs in controllers

**Resources**:
- Quick Reference: `apps/common-py/NAMING_CONVENTIONS.md`
- Complete Guide: `apps/common-py/USER_SERVICE_ARCHITECTURE.md`
- Test Examples: `apps/common-py/tests/test_dto_naming_conventions.py`

### Python
- **Version**: 3.12+
- **Formatter**: Ruff (enforce via CI)
- **Linter**: Ruff
- **Type Hints**: Required (mypy strict)
- **Docstrings**: Google-style for public APIs
- **Max Line Length**: 100 characters

### TypeScript/React
- **Version**: 5.0+, React 18+
- **Formatter**: Prettier (configured in .prettierrc)
- **Linter**: ESLint + TypeScript ESLint
- **Strict Mode**: True in tsconfig.json
- **Component Tests**: Vitest with Testing Library
- **Max Line Length**: 100 characters

## API Design

### Naming Conventions
- Routes: `/api/[resource]` (lowercase, plural nouns)
- Models: PascalCase for Pydantic classes
- Functions: snake_case for Python, camelCase for TypeScript

### Request/Response Structure
```python
# FastAPI uses Pydantic for automatic OpenAPI docs
from pydantic import BaseModel

class DocumentUploadRequest(BaseModel):
    filename: str
    content_type: str
    size_bytes: int

class DocumentResponse(BaseModel):
    id: str
    filename: str
    status: str  # pending, processing, complete, error
    created_at: datetime
```

## Testing Standards

### Coverage Requirements
- **API Routes**: ≥70% coverage
- **Business Logic**: ≥75% coverage
- **Critical Paths**: 100% coverage (auth, payments, core workflows)

### Test Organization
```
apps/api/tests/
├── conftest.py              # Fixtures and setup
├── test_health.py           # Health check endpoint
├── integration/
│   └── test_document_upload.py
├── unit/
│   └── test_services.py
└── __pycache__/
```

### Test Execution
```bash
# All tests
uv run pytest

# Specific file
uv run pytest apps/api/tests/test_health.py -v

# With coverage
uv run pytest --cov=src --cov-report=html

# Watch mode
uv run pytest-watch
```

## Containerization

### All Services Must
- Include multi-stage Dockerfile (build + runtime)
- Run as non-root user
- Implement health checks (liveness + readiness)
- Support graceful shutdown (SIGTERM handling)
- Target <5s cold start time

### Python Services
- Base image: `python:3.12-slim`
- Package manager: uv
- Health check: GET /health endpoint

### Node.js Services (UI)
- Base image: `node:20-alpine` (build) + `nginx:alpine` (runtime)
- Static files served via nginx
- Health check: nginx status endpoint

## Recent Changes

- **2025-01-13**: Updated structure for ai-project-template (apps/ui, apps/api, apps/functions, apps/common-py)
- **2025-01-13**: Added ui-lib shared component library
- **2025-01-13**: Consolidated API and Functions documentation
- **2025-12-16**: Initial Python 3.12+, Node.js 20+, TypeScript 5.0+ + FastAPI, React 18, Vite, uv, npm workspaces

<!-- MANUAL ADDITIONS START -->

## Service Details

### apps/ui
React + Vite frontend for agents and content workflows. Includes:
- Pages for agent interactions, document uploads, chat interfaces
- Shared component library (ui-lib) for reusable UI elements
- TypeScript strict mode, Tailwind CSS for styling
- Hosted on Azure Container Apps

### apps/api
Unified FastAPI backend serving both agents and content APIs. Includes:
- OpenAPI/Swagger documentation auto-generated
- Pydantic models for request/response validation
- Middleware for auth, logging, CORS
- Cosmos DB integration for persistence
- Hosted on Azure Container Apps

### apps/functions
Azure Functions for background processing (containerized). Includes:
- Timer triggers for scheduled tasks
- Service Bus triggers for async processing
- Blob Storage triggers for document processing
- Hosted on Azure Container Apps

### apps/common-py
Shared Python utilities and models:
- Data models used across API and Functions
- Service clients for Azure services
- Utilities for logging, config, auth

### apps/ui-lib
Shared TypeScript React components:
- Reusable UI components
- API client helpers
- TypeScript types and utilities
- Published as npm package

<!-- MANUAL ADDITIONS END -->
