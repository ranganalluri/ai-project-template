# Naming Conventions Quick Reference

## Summary

| Context | Convention | Example |
|---------|-----------|---------|
| **Python Fields** | `snake_case` | `user_id`, `first_name`, `created_at` |
| **Class Names** | `PascalCase` | `UserResponse`, `CreateUserCommand` |
| **JSON/API** | `camelCase` | `userId`, `firstName`, `createdAt` |
| **Constants** | `UPPER_SNAKE_CASE` | `MAX_PAGE_SIZE`, `API_VERSION` |
| **Private Fields** | `_snake_case` | `_internal_id`, `_cached_value` |
| **Modules** | `snake_case` | `user_service.py`, `user_commands.py` |

## Code Examples

### ✅ Correct

```python
from datetime import datetime
from common.dtos.base import BaseResponse

class UserResponse(BaseResponse):
    """Class name: PascalCase"""
    
    # Python fields: snake_case
    user_id: str
    first_name: str
    last_name: str
    email_address: str
    created_at: datetime
    last_login_at: datetime | None
    
# Python usage: snake_case
user = UserResponse(
    user_id="user-123",
    first_name="Jane",
    last_name="Doe",
    email_address="jane@example.com",
    created_at=datetime.now(),
    last_login_at=None
)

# JSON output: camelCase (automatic)
json_output = user.model_dump(by_alias=True)
# {
#   "userId": "user-123",
#   "firstName": "Jane",
#   "lastName": "Doe",
#   "emailAddress": "jane@example.com",
#   "createdAt": "2025-01-13T10:00:00",
#   "lastLoginAt": null
# }
```

### ❌ Incorrect

```python
# Don't use camelCase for Python fields
class UserResponse(BaseResponse):
    userId: str              # ❌ Wrong
    firstName: str           # ❌ Wrong
    emailAddress: str        # ❌ Wrong

# Don't use snake_case for class names
class user_response(BaseResponse):  # ❌ Wrong
    pass

# Don't use PascalCase for fields
class UserResponse(BaseResponse):
    UserId: str              # ❌ Wrong
    FirstName: str           # ❌ Wrong
```

## Pydantic Configuration

### Base DTO Setup

```python
# common/dtos/base.py
from pydantic import BaseModel, ConfigDict

def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])

class BaseDTO(BaseModel):
    model_config = ConfigDict(
        # Auto-convert snake_case → camelCase
        alias_generator=to_camel,
        
        # Accept both formats in input
        populate_by_name=True,
        
        # Forbid extra fields
        extra="forbid",
        
        # Validate on assignment
        validate_assignment=True,
    )
```

## Common Patterns

### 1. Simple Response

```python
class UserResponse(BaseDTO):
    user_id: str              # → userId
    first_name: str           # → firstName
    last_name: str            # → lastName
    email_address: str        # → emailAddress
    is_active: bool           # → isActive
    created_at: datetime      # → createdAt
```

### 2. Nested Objects

```python
class AddressResponse(BaseDTO):
    street_address: str       # → streetAddress
    city_name: str            # → cityName
    postal_code: str          # → postalCode
    
class UserResponse(BaseDTO):
    user_id: str              # → userId
    home_address: AddressResponse | None  # → homeAddress
    work_address: AddressResponse | None  # → workAddress
```

### 3. Lists and Collections

```python
class UserListResponse(BaseDTO):
    users: list[UserResponse]        # → users (stays same)
    total_count: int                 # → totalCount
    page_size: int                   # → pageSize
    current_page: int                # → currentPage
    total_pages: int                 # → totalPages
    has_next_page: bool              # → hasNextPage
    has_previous_page: bool          # → hasPreviousPage
```

### 4. Enums

```python
from enum import Enum

class AccountStatus(str, Enum):
    """Enum name: PascalCase, values: snake_case"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"

class UserResponse(BaseDTO):
    account_status: AccountStatus     # → accountStatus
    # JSON: "accountStatus": "active"
```

### 5. Optional Fields

```python
class UpdateUserCommand(BaseDTO):
    first_name: str | None = None     # → firstName
    last_name: str | None = None      # → lastName
    phone_number: str | None = None   # → phoneNumber
    
# Serialize only set fields
command = UpdateUserCommand(first_name="Jane")
json_data = command.model_dump(by_alias=True, exclude_unset=True)
# {"firstName": "Jane"}  ← only firstName included
```

## FastAPI Integration

```python
from fastapi import APIRouter
from common.dtos.commands import CreateUserCommand
from common.dtos.queries import UserResponse

router = APIRouter()

@router.post("/users", response_model=UserResponse)
async def create_user(command: CreateUserCommand) -> UserResponse:
    """
    FastAPI automatically:
    1. Accepts camelCase JSON in request
    2. Validates using Python snake_case
    3. Returns camelCase JSON in response
    
    Request body:
    {
        "firstName": "Jane",
        "lastName": "Doe",
        "emailAddress": "jane@example.com"
    }
    
    Response body:
    {
        "userId": "user-123",
        "firstName": "Jane",
        "lastName": "Doe",
        "emailAddress": "jane@example.com",
        "accountStatus": "active",
        "createdAt": "2025-01-13T10:00:00Z"
    }
    """
    return service.create_user(command)
```

## Testing

```python
def test_naming_conventions():
    """Test snake_case → camelCase conversion."""
    from common.dtos.queries import UserResponse
    
    # Python: snake_case
    user = UserResponse(
        user_id="123",
        first_name="Jane",
        email_address="jane@example.com",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # JSON: camelCase
    json_data = user.model_dump(by_alias=True)
    
    assert "userId" in json_data
    assert "firstName" in json_data
    assert "emailAddress" in json_data
    assert "createdAt" in json_data
    
    # snake_case NOT in JSON
    assert "user_id" not in json_data
    assert "first_name" not in json_data
```

## Common Conversions

| Python (snake_case) | JSON (camelCase) |
|---------------------|------------------|
| `user_id` | `userId` |
| `first_name` | `firstName` |
| `last_name` | `lastName` |
| `email_address` | `emailAddress` |
| `phone_number` | `phoneNumber` |
| `created_at` | `createdAt` |
| `updated_at` | `updatedAt` |
| `last_login_at` | `lastLoginAt` |
| `is_active` | `isActive` |
| `is_verified` | `isVerified` |
| `total_count` | `totalCount` |
| `page_size` | `pageSize` |
| `page_number` | `pageNumber` |
| `has_next_page` | `hasNextPage` |
| `account_status` | `accountStatus` |
| `billing_address` | `billingAddress` |

## Linting Rules

### Ruff Configuration

```toml
# pyproject.toml
[tool.ruff]
select = [
    "N",  # pep8-naming
]

[tool.ruff.pep8-naming]
# Enforce PascalCase for class names
classmethod-decorators = ["classmethod"]
# Enforce snake_case for functions
staticmethod-decorators = ["staticmethod"]
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix, --select, N]
```

## Validation Checklist

Before committing code:

- [ ] All class names use `PascalCase`
- [ ] All Python fields use `snake_case`
- [ ] All DTOs inherit from `BaseDTO` (or `BaseCommand`, `BaseQuery`, `BaseResponse`)
- [ ] JSON examples in docstrings use `camelCase`
- [ ] Tests verify both Python and JSON naming
- [ ] No hardcoded field names bypass alias_generator

## Resources

- [Pydantic Alias Documentation](https://docs.pydantic.dev/latest/concepts/alias/)
- [PEP 8 Naming Conventions](https://peps.python.org/pep-0008/#naming-conventions)
- Project: `USER_SERVICE_ARCHITECTURE.md` - Complete architecture guide
- Tests: `tests/test_dto_naming_conventions.py` - Comprehensive test suite
