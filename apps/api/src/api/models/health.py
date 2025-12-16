"""Health check response models."""

from pydantic import BaseModel
from typing import Optional


class HealthCheckResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str
    environment: Optional[str] = None
    message: str = "API is healthy"

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "status": "ok",
                "version": "0.1.0",
                "environment": "development",
                "message": "API is healthy",
            }
        }
