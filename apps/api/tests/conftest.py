"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def api_url() -> str:
    """Get the API base URL."""
    return "http://localhost:8000/api"
