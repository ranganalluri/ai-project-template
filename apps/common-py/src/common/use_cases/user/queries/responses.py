"""Response DTOs for user queries."""

from typing import Literal
from pydantic import Field, EmailStr
from common.dtos.base import BaseResponse


class UserResponse(BaseResponse):
    """Response DTO for user data.
    
    Python fields: snake_case
    JSON fields: camelCase (via alias_generator)
    """

    user_id: str = Field(..., description="Unique identifier for the user")
    first_name: str = Field(..., description="First name of the user")
    last_name: str = Field(..., description="Last name of the user")
    email_address: EmailStr = Field(..., description="Email address of the user")
    phone_number: str | None = Field(None, description="Phone number")
    account_status: Literal["active", "inactive", "suspended"] = Field(default="active", description="Account status")

    model_config = {
        "json_schema_extra": {
            "example": {
                # JSON example uses camelCase
                "userId": "user-123abc",
                "firstName": "Jane",
                "lastName": "Doe",
                "emailAddress": "jane.doe@example.com",
                "phoneNumber": "+1234567890",
                "accountStatus": "active"
            }
        }
    }


class UserListResponse(BaseResponse):
    """Response DTO for list of users with pagination."""

    users: list[UserResponse] = Field(description="List of users")
    total_count: int = Field(description="Total number of users")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of users per page")
    total_pages: int = Field(description="Total number of pages")
    has_next_page: bool = Field(description="Whether there are more pages")
    has_previous_page: bool = Field(description="Whether there are previous pages")

    model_config = {
        "json_schema_extra": {
            "example": {
                "users": [
                    {
                        "userId": "user-123",
                        "firstName": "Jane",
                        "lastName": "Doe",
                        "emailAddress": "jane.doe@example.com",
                        "accountStatus": "active",
                        "createdAt": "2025-01-13T10:00:00Z",
                        "updatedAt": "2025-01-13T10:00:00Z"
                    }
                ],
                "totalCount": 100,
                "page": 1,
                "pageSize": 20,
                "totalPages": 5,
                "hasNextPage": True,
                "hasPreviousPage": False
            }
        }
    }
