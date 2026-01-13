"""Query to list users with optional pagination."""

from typing import Literal
from pydantic import Field
from common.dtos.base import BaseQuery


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
