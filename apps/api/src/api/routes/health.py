"""Health check routes."""

from api.config import Settings, get_settings
from api.models.health import HealthCheckResponse
from api.services.foundry_client import FoundryClient
from fastapi import APIRouter, Depends

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    settings: Settings = Depends(get_settings),
) -> HealthCheckResponse:
    """Health check endpoint.

    Returns:
        HealthCheckResponse with status and version information
    """
    # Check Foundry configuration
    foundry_client = FoundryClient(settings)
    foundry_configured = foundry_client.is_configured()

    return HealthCheckResponse(
        status="ok",
        version=settings.app_version,
        environment=settings.environment,
        foundry_configured=foundry_configured,
    )
