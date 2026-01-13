"""User command DTOs for write operations."""

from pydantic import BaseModel, EmailStr, Field, field_validator
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


class UpdateUserCommand(BaseCommand):
    """Command to update an existing user.
    
    All fields are optional for partial updates.
    """

    first_name: str | None = Field(None, min_length=1, max_length=100, description="First name of the user")
    last_name: str | None = Field(None, min_length=1, max_length=100, description="Last name of the user")
    email_address: EmailStr | None = Field(None, description="Email address of the user")
    phone_number: str | None = Field(None, pattern=r"^\+?[1-9]\d{1,14}$", description="Phone number")
    
    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """Ensure names contain only letters, spaces, and hyphens."""
        if v is not None:
            if not v.replace(" ", "").replace("-", "").isalpha():
                raise ValueError("Names can only contain letters, spaces, and hyphens")
            return v.strip()
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "firstName": "Jane",
                "lastName": "Smith",
                "emailAddress": "jane.smith@example.com",
                "phoneNumber": "+1234567890"
            }
        }
    }


class DeleteUserCommand(BaseCommand):
    """Command to delete a user."""

    user_id: str = Field(..., description="Unique identifier for the user to delete")

    model_config = {
        "json_schema_extra": {
            "example": {
                "userId": "user-123abc",
            }
        }
    }
