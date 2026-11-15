"""Basic backend tests establishing the testing structure."""

from backend.tests.conftest import sample_task


def test_sample_task_fixture(sample_task):
    """The sample_task fixture provides a valid task dict."""
    assert sample_task["id"] == "task-001"
    assert sample_task["title"] == "Example task"
    assert sample_task["status"] == "pending"


def test_task_status_transition():
    """A task can transition from pending to completed."""
    task = {"id": "task-002", "title": "Another task", "status": "pending"}
    task["status"] = "completed"
    assert task["status"] == "completed"
