"""Pytest fixtures for StudySphere application and database testing."""

import pytest
from typing import Generator
from flask import Flask
from app import create_app
from app.extensions import db


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
def client(app: Flask):
    """Test client for HTTP requests."""
    return app.test_client()
