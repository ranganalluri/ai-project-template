"""Tests for the health check endpoint."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_health_check(client: TestClient) -> None:
    """Test the health check endpoint returns 200."""
    response = client.get("/api/health")
    assert response.status_code == 200


@pytest.mark.unit
def test_health_check_response_schema(client: TestClient) -> None:
    """Test the health check endpoint response has correct schema."""
    response = client.get("/api/health")
    data = response.json()

    assert "status" in data
    assert "version" in data
    assert "message" in data

    assert data["status"] == "ok"
    assert isinstance(data["version"], str)
    assert data["message"] == "API is healthy"


@pytest.mark.unit
def test_health_check_response_json() -> None:
    """Test health check response is valid JSON."""
    from api.models.health import HealthCheckResponse

    response = HealthCheckResponse(
        status="ok",
        version="0.1.0",
        environment="test",
    )

    # Should not raise
    response_dict = response.model_dump()
    assert response_dict["status"] == "ok"
