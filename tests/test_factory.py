"""Unit tests for the application factory and core configurations."""

import pytest
from flask import Flask
from app import create_app


def test_config_testing():
    """Ensure TestingConfig is loaded in testing mode."""
    app = create_app("testing")
    assert app.config["TESTING"] is True
    assert app.config["DEBUG"] is False


def test_production_requires_environment_secrets(monkeypatch):
    """Prevent production startup without its secret key and database URL."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="SECRET_KEY, DATABASE_URL"):
        create_app("production")


def test_production_uses_secure_session_cookies(monkeypatch):
    """Ensure production config enables secure cookie flags and disables debug."""
    monkeypatch.setenv("SECRET_KEY", "test-production-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    app = create_app("production")

    assert app.config["DEBUG"] is False
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


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
