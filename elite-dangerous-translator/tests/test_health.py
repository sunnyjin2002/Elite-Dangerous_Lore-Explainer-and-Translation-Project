"""Smoke tests for the FastAPI application."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_check() -> None:
    """Health endpoint returns an ok status."""
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dashboard() -> None:
    """Dashboard endpoint renders HTML."""
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "Elite Dangerous Translator" in response.text
