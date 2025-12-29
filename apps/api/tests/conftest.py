"""Pytest configuration and fixtures."""

import os
import sys

import pytest
from api.main import app
from fastapi.testclient import TestClient

# Ensure 'apps/api/src' is on sys.path for absolute 'api.*' imports
_TESTS_DIR = os.path.dirname(__file__)
_SRC_PATH = os.path.abspath(os.path.join(_TESTS_DIR, "..", "src"))
if _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)


@pytest.fixture
def client() -> TestClient:
    """Create a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def api_url() -> str:
    """Get the API base URL."""
    return "http://localhost:8000/api"
