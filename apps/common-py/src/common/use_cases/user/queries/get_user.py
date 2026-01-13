"""Query to get a user by ID."""

from pydantic import Field
from common.dtos.base import BaseQuery


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
