"""Pytest fixtures for StudySphere application and database testing."""

from __future__ import annotations
import pytest
from typing import Generator
from flask import Flask
from flask.testing import FlaskClient
from app import create_app
from app.extensions import db
from app.models.user import User


@pytest.fixture
def app() -> Generator[Flask, None, None]:
    """Create and configure a testing Flask app instance."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Test client for HTTP requests."""
    return app.test_client()


@pytest.fixture
def test_user(app: Flask) -> User:
    """Create and persist a default student user for testing."""
    with app.app_context():
        user = User(
            name="Test Student",
            email="student@example.com",
            semester=5,
        )
        user.set_password("SecurePassword123")
        db.session.add(user)
        db.session.commit()
        persisted = User.query.filter_by(email="student@example.com").first()
        assert persisted is not None
        return persisted


@pytest.fixture
def auth_client(client: FlaskClient, test_user: User) -> FlaskClient:
    """Provide a test client authenticated as the default test student."""
    client.post(
        "/auth/login",
        data={
            "email": "student@example.com",
            "password": "SecurePassword123",
        },
        follow_redirects=True,
    )
    return client
