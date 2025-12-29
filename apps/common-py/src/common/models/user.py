"""User model for User API."""

from typing import ClassVar

from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    """User entity model."""

    user_id: str = Field(..., description="Unique identifier for the user")
    name: str = Field(..., description="Full name of the user")
    email: EmailStr = Field(..., description="Email address of the user")

    class Config:
        """Pydantic config."""

        json_schema_extra: ClassVar[dict] = {
            "example": {
                "user_id": "user-123",
                "name": "Jane Doe",
                "email": "jane.doe@example.com",
            }
        }
