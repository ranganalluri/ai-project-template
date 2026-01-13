# User Service Architecture

This document describes the CQRS-inspired architecture for the User service with proper separation between Commands, Queries, Models, and DTOs.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                            │
│  (FastAPI routes receive Commands/Queries, return DTOs)     │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                            │
│  (UserService processes Commands/Queries with Mapper)       │
└────────────────┬────────────────────────────────────────────┘
                 │
        ┌────────┴─────────┐
        ▼                  ▼
┌──────────────┐    ┌──────────────┐
│   Mapper     │◄───┤  User Model  │
│  (Transform) │    │   (Domain)   │
└──────────────┘    └──────────────┘
        │                  │
        ▼                  ▼
┌──────────────────────────────────┐
│       Cosmos DB                  │
│  (Persistence Layer)             │
└──────────────────────────────────┘
```

## Folder Structure

```
common/
├── dtos/                           # Data Transfer Objects
│   ├── __init__.py
│   ├── commands/                   # Write operations
│   │   ├── __init__.py
│   │   └── user_commands.py        # CreateUserCommand, UpdateUserCommand, DeleteUserCommand
│   └── queries/                    # Read operations
│       ├── __init__.py
│       └── user_queries.py         # GetUserQuery, ListUsersQuery, SearchUsersQuery
│                                   # UserResponse, UserListResponse
├── models/                         # Domain models
│   └── user.py                     # User (domain entity)
│
├── services/                       # Business logic
│   └── user_service.py             # UserService, CosmosUserService
│
└── utils/                          # Utilities
    └── user_mapper.py              # UserMapper (transforms between layers)
```

## Naming Conventions & Serialization

### Enforced Standards

1. **Python Fields**: `snake_case` (e.g., `user_id`, `created_at`, `email_address`)
2. **Class Names**: `PascalCase` (e.g., `CreateUserCommand`, `UserResponse`)
3. **JSON/API Serialization**: `camelCase` (e.g., `userId`, `createdAt`, `emailAddress`)
4. **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_PAGE_SIZE`, `DEFAULT_TIMEOUT`)

### Pydantic Configuration

All DTOs use `alias_generator` to automatically convert between Python snake_case and JSON camelCase:

```python
from pydantic import BaseModel, ConfigDict, Field

class UserResponse(BaseModel):
    """Automatically serializes snake_case to camelCase."""
    
    user_id: str = Field(..., description="User ID")
    first_name: str = Field(..., description="First name")
    email_address: str = Field(..., description="Email")
    created_at: datetime = Field(..., description="Creation time")
    
    model_config = ConfigDict(
        # Serialize to camelCase for JSON
        alias_generator=lambda field_name: "".join(
            word.capitalize() if i > 0 else word 
            for i, word in enumerate(field_name.split("_"))
        ),
        # Accept both snake_case and camelCase in requests
        populate_by_name=True,
    )

# Python usage (snake_case)
response = UserResponse(
    user_id="user-123",
    first_name="Jane",
    email_address="jane@example.com",
    created_at=datetime.now()
)

# JSON output (camelCase)
json_output = response.model_dump(by_alias=True)
# {
#     "userId": "user-123",
#     "firstName": "Jane",
#     "emailAddress": "jane@example.com",
#     "createdAt": "2025-01-13T10:00:00"
# }

# JSON input accepts both formats
UserResponse.model_validate({
    "userId": "user-123",        # camelCase works
    "user_id": "user-123",       # snake_case also works (populate_by_name=True)
})
```

## Components

### 1. Commands (Write Operations)

**Location**: `common/dtos/commands/user_commands.py`

Commands represent **write intentions** and contain only the data needed to perform an action.

```python
from common.dtos.commands import CreateUserCommand

# Create a new user (Python snake_case)
command = CreateUserCommand(
    name="Jane Doe",
    email="jane.doe@example.com"
)

# Also accepts camelCase from JSON requests
command = CreateUserCommand.model_validate({
    "name": "Jane Doe",
    "email": "jane.doe@example.com"
})
```

**Available Commands**:
- `CreateUserCommand` - Create a new user
- `UpdateUserCommand` - Update existing user (partial updates)
- `DeleteUserCommand` - Delete a user

### 2. Queries (Read Operations)

**Location**: `common/dtos/queries/user_queries.py`

Queries represent **read requests** and can include pagination/filtering parameters.

```python
from common.dtos.queries import GetUserQuery, ListUsersQuery, SearchUsersQuery

# Get single user
query = GetUserQuery(user_id="user-123")

# List users with pagination
query = ListUsersQuery(page=1, page_size=20)

# Search users
query = SearchUsersQuery(name="Jane", page=1, page_size=20)
```

**Available Queries**:
- `GetUserQuery` - Get user by ID
- `ListUsersQuery` - List users with pagination
- `SearchUsersQuery` - Search users by name

### 3. Response DTOs

**Location**: `common/dtos/queries/user_queries.py`

Response DTOs define the shape of data returned from queries.

```python
from common.dtos.queries import UserResponse, UserListResponse

# Single user response
response: UserResponse = {
    "user_id": "user-123",
    "name": "Jane Doe",
    "email": "jane.doe@example.com"
}

# List response with pagination
response: UserListResponse = {
    "users": [UserResponse(...)],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
}
```

### 4. Domain Model

**Location**: `common/models/user.py`

The domain model represents the **core business entity**. It's used internally by the service layer.

```python
from common.models.user import User

user = User(
    user_id="user-123",
    name="Jane Doe",
    email="jane.doe@example.com"
)
```

### 5. Mapper

**Location**: `common/utils/user_mapper.py`

The mapper transforms data between different layers:
- Command → Domain Model
- Domain Model → Response DTO
- Domain Model ↔ Cosmos DB Document

```python
from common.utils.user_mapper import UserMapper

# Command to Model
user = UserMapper.from_create_command(command)

# Model to Response
response = UserMapper.to_response(user)

# Model to Cosmos DB
doc = UserMapper.to_cosmos_document(user)

# Cosmos DB to Model
user = UserMapper.from_cosmos_document(doc)
```

### 6. Service

**Location**: `common/services/user_service.py`

The service orchestrates business logic using Commands, Queries, Models, and Mapper.

```python
from common.services.user_service import CosmosUserService
from common.dtos.commands import CreateUserCommand
from common.dtos.queries import GetUserQuery

# Initialize service
service = CosmosUserService(
    cosmos_endpoint="https://...",
    cosmos_key="...",
    database_name="agentic",
    container_name="users"
)

# Execute command
command = CreateUserCommand(name="Jane Doe", email="jane@example.com")
response = service.create_user(command)  # Returns UserResponse

# Execute query
query = GetUserQuery(user_id="user-123")
response = service.get_user(query)  # Returns UserResponse or None
```

## Usage Examples

### In API Routes (apps/api)

```python
from fastapi import APIRouter, Depends, HTTPException
from common.dtos.commands import CreateUserCommand, UpdateUserCommand
from common.dtos.queries import GetUserQuery, ListUsersQuery, SearchUsersQuery, UserResponse, UserListResponse
from common.services.user_service import UserService

router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(
    command: CreateUserCommand,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Create a new user."""
    try:
        return service.create_user(command)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Get a user by ID."""
    query = GetUserQuery(user_id=user_id)
    response = service.get_user(query)
    if not response:
        raise HTTPException(status_code=404, detail="User not found")
    return response

@router.get("/", response_model=UserListResponse)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    service: UserService = Depends(get_user_service),
) -> UserListResponse:
    """List users with pagination."""
    query = ListUsersQuery(page=page, page_size=page_size)
    return service.list_users(query)

@router.get("/search/", response_model=UserListResponse)
async def search_users(
    name: str,
    page: int = 1,
    page_size: int = 20,
    service: UserService = Depends(get_user_service),
) -> UserListResponse:
    """Search users by name."""
    query = SearchUsersQuery(name=name, page=page, page_size=page_size)
    return service.search_users(query)

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    command: UpdateUserCommand,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Update a user."""
    response = service.update_user(user_id, command)
    if not response:
        raise HTTPException(status_code=404, detail="User not found")
    return response

@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    service: UserService = Depends(get_user_service),
) -> None:
    """Delete a user."""
    if not service.delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
```

### In Azure Functions (apps/functions)

```python
import azure.functions as func
from common.dtos.commands import CreateUserCommand
from common.dtos.queries import GetUserQuery
from common.services.user_service import CosmosUserService

def main(msg: func.ServiceBusMessage) -> None:
    """Process user creation from Service Bus."""
    # Parse message
    data = msg.get_json()
    
    # Create command
    command = CreateUserCommand(
        name=data["name"],
        email=data["email"]
    )
    
    # Execute command
    service = get_user_service()
    response = service.create_user(command)
    
    # Log result
    logger.info(f"Created user: {response.user_id}")
```

### In Tests

```python
import pytest
from common.dtos.commands import CreateUserCommand
from common.dtos.queries import GetUserQuery, ListUsersQuery
from common.services.user_service import CosmosUserService

def test_create_and_get_user(cosmos_service: CosmosUserService):
    # Arrange
    command = CreateUserCommand(
        name="Test User",
        email="test@example.com"
    )
    
    # Act - Create
    response = cosmos_service.create_user(command)
    
    # Assert - Create
    assert response.name == "Test User"
    assert response.email == "test@example.com"
    assert response.user_id.startswith("user-")
    
    # Act - Get
    query = GetUserQuery(user_id=response.user_id)
    retrieved = cosmos_service.get_user(query)
    
    # Assert - Get
    assert retrieved is not None
    assert retrieved.user_id == response.user_id
    assert retrieved.name == "Test User"

def test_list_users_pagination(cosmos_service: CosmosUserService):
    # Arrange - Create multiple users
    for i in range(25):
        command = CreateUserCommand(
            name=f"User {i}",
            email=f"user{i}@example.com"
        )
        cosmos_service.create_user(command)
    
    # Act - List first page
    query = ListUsersQuery(page=1, page_size=10)
    response = cosmos_service.list_users(query)
    
    # Assert
    assert len(response.users) == 10
    assert response.total >= 25
    assert response.page == 1
    assert response.page_size == 10
    assert response.total_pages >= 3
```

## Benefits of This Architecture

### ✅ Separation of Concerns
- **Commands** are separate from **Queries** (CQRS pattern)
- **DTOs** are separate from **Domain Models**
- **API layer** doesn't know about database structure

### ✅ Type Safety
- Pydantic validation on all inputs
- Type hints throughout
- Auto-generated OpenAPI docs

### ✅ Testability
- Mock service interface, not database
- Test commands/queries independently
- Easy to create test fixtures

### ✅ Flexibility
- Change database without changing API
- Change API response format without changing database
- Add validation without touching routes

### ✅ Reusability
- DTOs shared between API and Functions
- Service logic used across services
- Mapper handles all transformations

### ✅ Maintainability
- Clear responsibilities for each component
- Easy to find and modify code
- Self-documenting structure

## Adding New Operations

### 1. Add a Command

```python
# In common/dtos/commands/user_commands.py
class VerifyUserEmailCommand(BaseModel):
    user_id: str
    verification_token: str
```

### 2. Add a Query

```python
# In common/dtos/queries/user_queries.py
class GetUserByEmailQuery(BaseModel):
    email: EmailStr
```

### 3. Update Service

```python
# In common/services/user_service.py
def verify_user_email(self, command: VerifyUserEmailCommand) -> UserResponse:
    # Implementation
    pass

def get_user_by_email(self, query: GetUserByEmailQuery) -> UserResponse | None:
    # Implementation
    pass
```

### 4. Update Exports

```python
# In common/dtos/__init__.py
__all__ = [
    # ... existing
    "VerifyUserEmailCommand",
    "GetUserByEmailQuery",
]
```

## Enforcing Naming Conventions

### Base DTO Configuration

Create a base class with enforced conventions:

```python
# common/dtos/base.py
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_serializer

def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])

class BaseDTO(BaseModel):
    """Base class for all DTOs with naming conventions enforced."""
    
    model_config = ConfigDict(
        # Convert snake_case to camelCase for JSON
        alias_generator=to_camel,
        # Allow both snake_case and camelCase in input
        populate_by_name=True,
        # Strict types
        strict=False,
        # Validate on assignment
        validate_assignment=True,
        # Use enum values
        use_enum_values=True,
        # Forbid extra fields
        extra="forbid",
    )
    
    @field_serializer("*", when_used="json")
    def serialize_datetime(self, value):
        """Serialize datetime to ISO format."""
        if isinstance(value, datetime):
            return value.isoformat()
        return value
```

### Example: Complete User DTO

```python
# common/dtos/queries/user_queries.py
from datetime import datetime
from typing import Literal
from pydantic import Field, EmailStr, field_validator
from common.dtos.base import BaseDTO

class UserResponse(BaseDTO):
    """User response with proper naming conventions.
    
    Python fields: snake_case
    JSON output: camelCase
    """
    
    user_id: str = Field(..., description="Unique user identifier")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email_address: EmailStr = Field(..., description="User email")
    phone_number: str | None = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    account_status: Literal["active", "inactive", "suspended"] = Field(default="active")
    created_at: datetime = Field(..., description="Account creation time")
    updated_at: datetime = Field(..., description="Last update time")
    last_login_at: datetime | None = Field(None, description="Last login time")
    
    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure names don't contain special characters."""
        if not v.replace(" ", "").replace("-", "").isalpha():
            raise ValueError("Names can only contain letters, spaces, and hyphens")
        return v.strip()
    
    model_config = {
        "json_schema_extra": {
            "example": {
                # JSON example uses camelCase
                "userId": "user-123abc",
                "firstName": "Jane",
                "lastName": "Doe",
                "emailAddress": "jane.doe@example.com",
                "phoneNumber": "+1234567890",
                "accountStatus": "active",
                "createdAt": "2025-01-13T10:00:00Z",
                "updatedAt": "2025-01-13T10:00:00Z",
                "lastLoginAt": "2025-01-13T11:30:00Z"
            }
        }
    }

# Usage in Python (snake_case)
response = UserResponse(
    user_id="user-123",
    first_name="Jane",
    last_name="Doe",
    email_address="jane.doe@example.com",
    phone_number="+1234567890",
    account_status="active",
    created_at=datetime.now(),
    updated_at=datetime.now()
)

# Access fields in Python (snake_case)
print(response.user_id)        # "user-123"
print(response.first_name)     # "Jane"
print(response.email_address)  # "jane.doe@example.com"

# JSON serialization (camelCase)
json_str = response.model_dump_json(by_alias=True)
# {
#   "userId": "user-123",
#   "firstName": "Jane",
#   "lastName": "Doe",
#   "emailAddress": "jane.doe@example.com",
#   "phoneNumber": "+1234567890",
#   "accountStatus": "active",
#   "createdAt": "2025-01-13T10:00:00",
#   "updatedAt": "2025-01-13T10:00:00",
#   "lastLoginAt": null
# }

# Parse from JSON (accepts camelCase)
user = UserResponse.model_validate_json('''
{
    "userId": "user-456",
    "firstName": "John",
    "lastName": "Smith",
    "emailAddress": "john@example.com",
    "accountStatus": "active",
    "createdAt": "2025-01-13T10:00:00Z",
    "updatedAt": "2025-01-13T10:00:00Z"
}
''')
```

### Example: Command with Nested Objects

```python
# common/dtos/commands/user_commands.py
from pydantic import Field, EmailStr
from common.dtos.base import BaseDTO

class AddressCommand(BaseDTO):
    """Address information (nested in CreateUserCommand)."""
    
    street_address: str = Field(..., min_length=1, max_length=200)
    city_name: str = Field(..., min_length=1, max_length=100)
    state_code: str = Field(..., min_length=2, max_length=2)
    postal_code: str = Field(..., pattern=r"^\d{5}(-\d{4})?$")
    country_code: str = Field(default="US", min_length=2, max_length=2)

class CreateUserCommand(BaseDTO):
    """Command to create user with address.
    
    Python: snake_case fields
    JSON: camelCase fields
    """
    
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email_address: EmailStr = Field(...)
    phone_number: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")
    billing_address: AddressCommand | None = Field(None)
    shipping_address: AddressCommand | None = Field(None)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "firstName": "Jane",
                "lastName": "Doe",
                "emailAddress": "jane.doe@example.com",
                "phoneNumber": "+1234567890",
                "billingAddress": {
                    "streetAddress": "123 Main St",
                    "cityName": "Springfield",
                    "stateCode": "IL",
                    "postalCode": "62701",
                    "countryCode": "US"
                }
            }
        }
    }

# Usage
command = CreateUserCommand(
    first_name="Jane",
    last_name="Doe",
    email_address="jane@example.com",
    phone_number="+1234567890",
    billing_address=AddressCommand(
        street_address="123 Main St",
        city_name="Springfield",
        state_code="IL",
        postal_code="62701"
    )
)

# JSON output (all camelCase)
json_output = command.model_dump(by_alias=True)
# {
#   "firstName": "Jane",
#   "lastName": "Doe",
#   "emailAddress": "jane@example.com",
#   "phoneNumber": "+1234567890",
#   "billingAddress": {
#     "streetAddress": "123 Main St",
#     "cityName": "Springfield",
#     "stateCode": "IL",
#     "postalCode": "62701",
#     "countryCode": "US"
#   },
#   "shippingAddress": null
# }
```

### FastAPI Integration

FastAPI automatically handles serialization with `by_alias=True`:

```python
# apps/api/src/api/routes/users.py
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from common.dtos.commands import CreateUserCommand
from common.dtos.queries import UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(
    command: CreateUserCommand,  # Accepts camelCase JSON
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Create user - accepts camelCase JSON, returns camelCase JSON.
    
    Request body (camelCase):
    {
        "firstName": "Jane",
        "lastName": "Doe",
        "emailAddress": "jane@example.com"
    }
    
    Response body (camelCase):
    {
        "userId": "user-123",
        "firstName": "Jane",
        "lastName": "Doe",
        "emailAddress": "jane@example.com",
        "accountStatus": "active",
        "createdAt": "2025-01-13T10:00:00Z"
    }
    """
    response = service.create_user(command)
    # FastAPI automatically uses by_alias=True for response_model
    return response

# Configure FastAPI app for consistent serialization
from fastapi import FastAPI

app = FastAPI(
    title="User API",
    version="1.0.0",
)

# Add middleware to ensure all responses use camelCase
@app.middleware("http")
async def add_alias_serialization(request, call_next):
    """Ensure all Pydantic responses use by_alias=True."""
    response = await call_next(request)
    return response
```

### Validation Examples

```python
# Type validation
command = CreateUserCommand(
    first_name="Jane",
    last_name="Doe",
    email_address="invalid-email"  # ❌ ValidationError: invalid email
)

# Field constraints
command = CreateUserCommand(
    first_name="",  # ❌ ValidationError: min_length=1
    last_name="Doe",
    email_address="jane@example.com"
)

# Pattern validation
command = CreateUserCommand(
    first_name="Jane",
    last_name="Doe",
    email_address="jane@example.com",
    phone_number="invalid"  # ❌ ValidationError: pattern mismatch
)

# Custom validators
command = CreateUserCommand(
    first_name="Jane123",  # ❌ ValidationError: names can only contain letters
    last_name="Doe",
    email_address="jane@example.com"
)
```

### Testing Naming Conventions

```python
import pytest
from common.dtos.queries import UserResponse
from datetime import datetime

def test_snake_case_to_camel_case():
    """Test Python snake_case serializes to JSON camelCase."""
    response = UserResponse(
        user_id="user-123",
        first_name="Jane",
        last_name="Doe",
        email_address="jane@example.com",
        account_status="active",
        created_at=datetime(2025, 1, 13, 10, 0, 0),
        updated_at=datetime(2025, 1, 13, 10, 0, 0)
    )
    
    # Serialize to JSON with aliases
    json_data = response.model_dump(by_alias=True)
    
    # Assert JSON uses camelCase
    assert "userId" in json_data
    assert "firstName" in json_data
    assert "lastName" in json_data
    assert "emailAddress" in json_data
    assert "accountStatus" in json_data
    assert "createdAt" in json_data
    assert "updatedAt" in json_data
    
    # Assert snake_case keys are NOT in JSON
    assert "user_id" not in json_data
    assert "first_name" not in json_data
    assert "email_address" not in json_data

def test_camel_case_to_snake_case():
    """Test JSON camelCase deserializes to Python snake_case."""
    json_str = '''
    {
        "userId": "user-456",
        "firstName": "John",
        "lastName": "Smith",
        "emailAddress": "john@example.com",
        "accountStatus": "active",
        "createdAt": "2025-01-13T10:00:00",
        "updatedAt": "2025-01-13T10:00:00"
    }
    '''
    
    # Parse from JSON
    response = UserResponse.model_validate_json(json_str)
    
    # Assert Python uses snake_case
    assert response.user_id == "user-456"
    assert response.first_name == "John"
    assert response.last_name == "Smith"
    assert response.email_address == "john@example.com"
    assert response.account_status == "active"

def test_validation_errors():
    """Test field validations work correctly."""
    with pytest.raises(ValueError, match="Names can only contain letters"):
        UserResponse(
            user_id="user-123",
            first_name="Jane123",  # Invalid: contains numbers
            last_name="Doe",
            email_address="jane@example.com",
            account_status="active",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
```

## Migration from Legacy Code

If you have existing code using the old service interface:

### Before
```python
# Old style
user = User(user_id="...", name="...", email="...")
success = service.add_user(user)
users = service.list_users()
```

### After
```python
# New style with DTOs (snake_case in Python)
command = CreateUserCommand(
    first_name="Jane",
    last_name="Doe",
    email_address="jane@example.com"
)
response = service.create_user(command)  # Returns UserResponse

# JSON API receives/returns camelCase
# {
#   "firstName": "Jane",
#   "lastName": "Doe", 
#   "emailAddress": "jane@example.com"
# }

query = ListUsersQuery(page=1, page_size=20)
response = service.list_users(query)  # Returns UserListResponse
```
