"""Health check routes."""

from fastapi import APIRouter, Depends

from src.api.config import Settings, get_settings
from src.api.models.health import HealthCheckResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthCheckResponse:
    """Health check endpoint.

    Returns:
        HealthCheckResponse with status and version information
    """
    return HealthCheckResponse(
        status="ok",
        version=settings.app_version,
        environment=settings.environment,
    )
