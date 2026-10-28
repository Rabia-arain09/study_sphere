"""Unit tests for the application factory and core configurations."""

from flask import Flask
from app import create_app


def test_config_testing():
    """Ensure TestingConfig is loaded in testing mode."""
    app = create_app("testing")
    assert app.config["TESTING"] is True
    assert app.config["DEBUG"] is False


def test_health_check(client):
    """Ensure health endpoint returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {
        "status": "healthy",
        "service": "studysphere-api",
    }


def test_blueprints_registered(app: Flask):
    """Verify that all required blueprints are registered."""
    expected_blueprints = {"auth", "topics", "quiz", "upload", "dashboard"}
    registered_blueprints = set(app.blueprints.keys())
    assert expected_blueprints.issubset(registered_blueprints)
