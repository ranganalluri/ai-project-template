"""Command to update an existing user."""

from pydantic import Field, field_validator, EmailStr
from common.dtos.base import BaseCommand


class UpdateUserCommand(BaseCommand):
    """Command to update an existing user.
    
    Python fields: snake_case
    JSON fields: camelCase (via alias_generator)
    """

    user_id: str = Field(..., min_length=1, description="Unique identifier of the user to update")
    first_name: str | None = Field(None, min_length=1, max_length=100, description="First name of the user")
    last_name: str | None = Field(None, min_length=1, max_length=100, description="Last name of the user")
    email_address: EmailStr | None = Field(None, description="Email address of the user")
    phone_number: str | None = Field(None, pattern=r"^\+?[1-9]\d{1,14}$", description="Phone number (E.164 format)")
    
    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """Ensure names contain only letters, spaces, and hyphens."""
        if v is None:
            return v
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
                "phoneNumber": "+1234567890"
            }
        }
    }
