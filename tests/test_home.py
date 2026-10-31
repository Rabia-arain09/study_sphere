"""Unit tests for the home landing page and content negotiation."""

from __future__ import annotations
from flask.testing import FlaskClient
from app.models.user import User


def test_home_page_html_unauthenticated(client: FlaskClient):
    """Verify home page renders introduction and call to action for visitors."""
    response = client.get("/", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert b"Master Your Computer Science Curriculum" in response.data
    assert b"Get Started Free" in response.data
    assert b"Sign In to Account" in response.data


def test_home_page_html_authenticated(auth_client: FlaskClient):
    """Verify home page renders personalized call to action for logged-in students."""
    response = auth_client.get("/", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert b"Browse Semester 5 Notes" in response.data
    assert b"View My Subjects" in response.data


def test_home_page_json_content_negotiation(client: FlaskClient):
    """Verify root / returns API status JSON when application/json is explicitly requested."""
    response = client.get("/", headers={"Accept": "application/json"})
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert data["status"] == "online"
    assert data["message"] == "Welcome to StudySphere API"
