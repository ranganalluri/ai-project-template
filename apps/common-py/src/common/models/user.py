"""User model for User API."""

from typing import ClassVar

from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    """User entity model aligned with CreateUserCommand."""

    user_id: str = Field(..., description="Unique identifier for the user")
    first_name: str = Field(..., description="First name of the user")
    last_name: str = Field(..., description="Last name of the user")
    email_address: EmailStr = Field(..., description="Email address of the user")
    phone_number: str | None = Field(None, description="Phone number (E.164 format)")

    class Config:
        """Pydantic config."""

        json_schema_extra: ClassVar[dict] = {
            "example": {
                "user_id": "user-123",
                "first_name": "Jane",
                "last_name": "Doe",
                "email_address": "jane.doe@example.com",
                "phone_number": "+1234567890",
            }
        }
