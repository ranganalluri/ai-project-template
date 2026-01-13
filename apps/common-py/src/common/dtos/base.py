"""Base DTO classes with enforced naming conventions."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_serializer


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase.
    
    Examples:
        user_id -> userId
        first_name -> firstName
        created_at -> createdAt
        
    Args:
        string: snake_case field name
        
    Returns:
        camelCase field name
    """
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class BaseDTO(BaseModel):
    """Base class for all DTOs with naming conventions enforced.
    
    Conventions:
    - Python fields: snake_case (user_id, created_at)
    - Class names: PascalCase (UserResponse, CreateUserCommand)
    - JSON output: camelCase (userId, createdAt)
    - Constants: UPPER_SNAKE_CASE (MAX_PAGE_SIZE)
    
    Configuration:
    - alias_generator: Converts snake_case to camelCase for JSON
    - populate_by_name: Accepts both snake_case and camelCase in input
    - strict: Type validation (default: False for flexibility)
    - validate_assignment: Validate when fields are assigned
    - use_enum_values: Use string values for enums in JSON
    - extra: Forbid extra fields not defined in model
    
    Example:
        class UserResponse(BaseDTO):
            user_id: str
            first_name: str
            email_address: str
            
        # Python usage (snake_case)
        user = UserResponse(
            user_id="123",
            first_name="Jane",
            email_address="jane@example.com"
        )
        
        # JSON output (camelCase)
        json_data = user.model_dump(by_alias=True)
        # {"userId": "123", "firstName": "Jane", "emailAddress": "jane@example.com"}
    """
    
    model_config = ConfigDict(
        # Convert snake_case to camelCase for JSON serialization
        alias_generator=to_camel,
        
        # Allow both snake_case and camelCase in input (for flexibility)
        populate_by_name=True,
        
        # Type validation (False for more flexible parsing)
        strict=False,
        
        # Validate fields when assigned after initialization
        validate_assignment=True,
        
        # Use enum values (strings) instead of enum objects in JSON
        use_enum_values=True,
        
        # Forbid extra fields not defined in the model
        extra="forbid",
        
        # Arbitrary types not allowed (use Pydantic types)
        arbitrary_types_allowed=False,
    )
    
    @field_serializer("*", when_used="json")
    def serialize_datetime(self, value):
        """Serialize datetime to ISO 8601 format.
        
        Args:
            value: Field value (any type)
            
        Returns:
            ISO formatted string for datetime, original value otherwise
        """
        if isinstance(value, datetime):
            return value.isoformat()
        return value


class BaseCommand(BaseDTO):
    """Base class for Command DTOs (write operations).
    
    Commands represent write intentions and should:
    - Contain only the data needed to perform the action
    - Be validated before processing
    - Not include computed or derived fields
    - Use present tense (CreateUserCommand, not UserCreatedCommand)
    
    Example:
        class CreateUserCommand(BaseCommand):
            first_name: str
            last_name: str
            email_address: str
    """
    pass


class BaseQuery(BaseDTO):
    """Base class for Query DTOs (read operations).
    
    Queries represent read requests and can include:
    - Filtering parameters
    - Pagination parameters
    - Sorting parameters
    - Field selection parameters
    
    Example:
        class ListUsersQuery(BaseQuery):
            page: int = 1
            page_size: int = 20
            sort_by: str = "created_at"
            sort_order: str = "desc"
    """
    pass


class BaseResponse(BaseDTO):
    """Base class for Response DTOs (output from queries).
    
    Responses define the shape of data returned and should:
    - Include all relevant data for the client
    - Use computed fields for derived data
    - Follow consistent patterns across similar entities
    
    Example:
        class UserResponse(BaseResponse):
            user_id: str
            first_name: str
            email_address: str
            created_at: datetime
    """
    pass
