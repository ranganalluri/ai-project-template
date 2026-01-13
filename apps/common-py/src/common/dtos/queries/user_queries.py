"""User query DTOs for read operations."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, EmailStr
from common.dtos.base import BaseQuery, BaseResponse


class GetUserQuery(BaseQuery):
    """Query to get a user by ID."""

    user_id: str = Field(..., description="Unique identifier for the user")

    model_config = {
        "json_schema_extra": {
            "example": {
                "userId": "user-123abc",
            }
        }
    }


class ListUsersQuery(BaseQuery):
    """Query to list users with optional pagination."""

    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=100, description="Number of users per page")
    sort_by: str | None = Field(None, description="Field to sort by (e.g., 'createdAt', 'lastName')")
    sort_order: Literal["asc", "desc"] = Field("desc", description="Sort order")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "page": 1,
                "pageSize": 20,
                "sortBy": "createdAt",
                "sortOrder": "desc"
            }
        }
    }


class SearchUsersQuery(BaseQuery):
    """Query to search users by name."""

    search_term: str = Field(..., min_length=1, max_length=200, description="Search term for name matching")
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=100, description="Number of users per page")

    model_config = {
        "json_schema_extra": {
            "example": {
                "searchTerm": "Jane",
                "page": 1,
                "pageSize": 20,
            }
        }
    }


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
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_login_at: datetime | None = Field(None, description="Last login timestamp")

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
