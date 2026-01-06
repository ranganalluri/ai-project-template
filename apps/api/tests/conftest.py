"""Pytest configuration and fixtures."""

import pytest
from api.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """Create a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def api_url() -> str:
    """Get the API base URL."""
    return "http://localhost:8000/api"
