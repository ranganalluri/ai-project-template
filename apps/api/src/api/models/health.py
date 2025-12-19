"""Health check response models."""

from typing import ClassVar

from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str
    environment: str | None = None
    message: str = "API is healthy"

    class Config:
        """Pydantic config."""

        json_schema_extra: ClassVar[dict] = {
            "example": {
                "status": "ok",
                "version": "0.1.0",
                "environment": "development",
                "message": "API is healthy",
            }
        }
