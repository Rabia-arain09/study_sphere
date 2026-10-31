"""Unit tests for the authentication blueprint (registration, login, logout, security)."""

from __future__ import annotations
from flask.testing import FlaskClient
from app.extensions import db
from app.models.user import User


def test_signup_page_renders(client: FlaskClient):
    """Ensure GET /auth/signup renders registration form."""
    response = client.get("/auth/signup")
    assert response.status_code == 200
    assert b"Join StudySphere" in response.data
    assert b"Create Account" in response.data


def test_signup_successful(client: FlaskClient, app):
    """Verify student registration creates DB record, hashes password, and logs in."""
    payload = {
        "name": "Jane Developer",
        "email": "jane@example.com",
        "password": "StrongPassword123",
        "semester": 4,
    }
    response = client.post("/auth/signup", data=payload, follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome to StudySphere, Jane Developer!" in response.data
    assert b"Curriculum Subjects" in response.data

    with app.app_context():
        user = User.query.filter_by(email="jane@example.com").first()
        assert user is not None
        assert user.name == "Jane Developer"
        assert user.semester == 4
        assert user.password_hash != "StrongPassword123"
        assert user.check_password("StrongPassword123") is True


def test_signup_duplicate_email_rejected(client: FlaskClient, test_user: User):
    """Verify signup rejects duplicate emails (case-insensitive) with clear error."""
    payload = {
        "name": "Another User",
        "email": "STUDENT@example.com",  # Same as test_user email in different case
        "password": "Password999",
        "semester": 2,
    }
    response = client.post("/auth/signup", data=payload, follow_redirects=False)
    assert response.status_code == 200
    assert b"An account with this email address already exists" in response.data


def test_signup_invalid_data(client: FlaskClient):
    """Verify signup enforces minimum password length and required fields."""
    payload = {
        "name": "",
        "email": "not-an-email",
        "password": "123",  # Too short (< 6 chars)
        "semester": 9,    # Out of range (1-8)
    }
    response = client.post("/auth/signup", data=payload, follow_redirects=False)
    assert response.status_code == 200
    assert b"Please provide your full name" in response.data
    assert b"Password must be at least 6 characters long" in response.data


def test_login_page_renders(client: FlaskClient):
    """Ensure GET /auth/login renders login form."""
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert b"Welcome Back" in response.data
    assert b"Sign In" in response.data


def test_login_successful(client: FlaskClient, test_user: User):
    """Verify login with correct credentials authenticates the session."""
    payload = {
        "email": "student@example.com",
        "password": "SecurePassword123",
    }
    response = client.post("/auth/login", data=payload, follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back, Test Student!" in response.data
    assert b"Logout" in response.data


def test_login_invalid_password(client: FlaskClient, test_user: User):
    """Verify login fails when given an incorrect password."""
    payload = {
        "email": "student@example.com",
        "password": "WrongPassword!",
    }
    response = client.post("/auth/login", data=payload, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid email or password" in response.data
    assert b"Logout" not in response.data


def test_login_nonexistent_user(client: FlaskClient):
    """Verify login fails for unregistered email address."""
    payload = {
        "email": "ghost@example.com",
        "password": "AnyPassword123",
    }
    response = client.post("/auth/login", data=payload, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid email or password" in response.data


def test_logout(auth_client: FlaskClient):
    """Verify logout terminates session and redirects to login."""
    response = auth_client.get("/auth/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been signed out successfully." in response.data
    assert b"Sign In" in response.data

    # Protected page should now redirect to login
    protected = auth_client.get("/topics/")
    assert protected.status_code == 302
    assert "/auth/login" in protected.headers["Location"]


def test_login_required_redirect(client: FlaskClient):
    """Verify unauthenticated requests to protected endpoints redirect to login."""
    response = client.get("/topics/")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]
    assert "next=" in response.headers["Location"]


def test_safe_next_redirect_valid(client: FlaskClient, test_user: User):
    """Verify safe internal 'next' URL is respected upon login."""
    response = client.post(
        "/auth/login?next=/topics/semester/5",
        data={
            "email": "student@example.com",
            "password": "SecurePassword123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/topics/semester/5"


def test_safe_next_redirect_rejects_external_url(client: FlaskClient, test_user: User):
    """Verify malicious external 'next' targets are rejected and fall back safely."""
    malicious_targets = [
        "https://evil.com",
        "http://attacker.org/steal",
        "//evil.com",
        "javascript:alert(1)",
    ]
    for target in malicious_targets:
        response = client.post(
            f"/auth/login?next={target}",
            data={
                "email": "student@example.com",
                "password": "SecurePassword123",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        # Must redirect internally, not to external target
        assert not response.headers["Location"].startswith(("http:", "https:", "//"))
        assert "/topics" in response.headers["Location"]


def test_authenticated_user_redirected_from_login_signup(auth_client: FlaskClient):
    """Verify already-authenticated users visiting /auth/login or /auth/signup are redirected."""
    login_resp = auth_client.get("/auth/login", follow_redirects=False)
    assert login_resp.status_code == 302
    assert "/topics" in login_resp.headers["Location"]

    signup_resp = auth_client.get("/auth/signup", follow_redirects=False)
    assert signup_resp.status_code == 302
    assert "/topics" in signup_resp.headers["Location"]
