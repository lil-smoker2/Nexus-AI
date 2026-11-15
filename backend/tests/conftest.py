"""Pytest configuration for NEXUS AI backend tests."""

import pytest


@pytest.fixture
def sample_task():
    """Return a sample task dict for tests."""
    return {
        "id": "task-001",
        "title": "Example task",
        "status": "pending",
    }

