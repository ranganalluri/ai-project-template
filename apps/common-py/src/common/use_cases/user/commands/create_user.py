"""Command to create a new user."""

from pydantic import Field, field_validator, EmailStr
from common.dtos.base import BaseCommand


class CreateUserCommand(BaseCommand):
    """Command to create a new user.
    
    Python fields: snake_case
    JSON fields: camelCase (via alias_generator)
    """

    first_name: str = Field(..., min_length=1, max_length=100, description="First name of the user")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name of the user")
    email_address: EmailStr = Field(..., description="Email address of the user")
    phone_number: str | None = Field(None, pattern=r"^\+?[1-9]\d{1,14}$", description="Phone number (E.164 format)")
    
    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure names contain only letters, spaces, and hyphens."""
        if not v.replace(" ", "").replace("-", "").isalpha():
            raise ValueError("Names can only contain letters, spaces, and hyphens")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                # JSON example uses camelCase
                "firstName": "Jane",
                "lastName": "Doe",
                "emailAddress": "jane.doe@example.com",
                "phoneNumber": "+1234567890"
            }
        }
    }
