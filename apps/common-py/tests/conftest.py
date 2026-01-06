"""Pytest configuration for common-py tests."""

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests that make real API calls"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
