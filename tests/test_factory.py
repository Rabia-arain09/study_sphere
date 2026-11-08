"""Unit tests for the application factory and core configurations."""

import pytest
from flask import Flask, Response, jsonify, request, url_for
from app import create_app


def test_config_testing() -> None:
    """Ensure TestingConfig is loaded in testing mode."""
    app = create_app("testing")
    assert app.config["TESTING"] is True
    assert app.config["DEBUG"] is False


def test_production_requires_environment_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prevent production startup without its secret key and database URL."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="SECRET_KEY, DATABASE_URL"):
        create_app("production")


def test_production_uses_secure_session_cookies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure production config enables secure cookie flags and disables debug."""
    monkeypatch.setenv("SECRET_KEY", "test-production-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    app = create_app("production")

    assert app.config["DEBUG"] is False
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_production_respects_forwarded_https_and_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use one proxy hop for secure request detection and generated URLs."""
    monkeypatch.setenv("SECRET_KEY", "test-production-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    app = create_app("production")

    @app.get("/proxy-check")
    def proxy_check() -> Response:
        return jsonify(
            secure=request.is_secure,
            health_url=url_for("health_check", _external=True),
        )

    response = app.test_client().get(
        "/proxy-check",
        headers={
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "studysphere.example",
            "X-Forwarded-Port": "443",
        },
    )

    assert response.get_json() == {
        "secure": True,
        "health_url": "https://studysphere.example/health",
    }


def test_testing_app_ignores_forwarded_https_header() -> None:
    """Do not apply production proxy behavior to local and test configurations."""
    app = create_app("testing")

    @app.get("/proxy-check")
    def proxy_check() -> Response:
        return jsonify(secure=request.is_secure)

    response = app.test_client().get(
        "/proxy-check",
        headers={"X-Forwarded-Proto": "https"},
    )

    assert response.get_json() == {"secure": False}


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
