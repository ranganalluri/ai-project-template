"""Query to search users by name."""

from pydantic import Field
from common.dtos.base import BaseQuery


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
