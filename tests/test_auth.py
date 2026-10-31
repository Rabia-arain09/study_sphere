"""Unit tests for the authentication blueprint (registration, login, logout, security)."""

from __future__ import annotations
from flask import g
from flask.testing import FlaskClient
from app.extensions import db
from app.models.user import User
from app.models.course import Course
from app.models.topic import Topic


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


def test_regression_user_loader_session_routes(client: FlaskClient, app):
    """Regression test: signup, login, and verify /, /topics/, and topic page with same client."""
    with app.app_context():
        course = Course(
            code="CS301",
            title="Operating Systems",
            semester=5,
            domain="Computing Core",
            credit_hours=3,
            contact_hours="3-0",
        )
        db.session.add(course)
        db.session.commit()

        topic = Topic(
            course_id=course.id,
            semester=5,
            subject="Operating Systems",
            name="Virtual Memory",
            difficulty=3,
            content="# Virtual Memory\n\nPaging architecture.",
        )
        db.session.add(topic)
        db.session.commit()
        topic_id = topic.id

    # 1. Sign up a new user with client
    signup_payload = {
        "name": "Session Tester",
        "email": "session.tester@example.com",
        "password": "Password123!",
        "semester": 5,
    }
    signup_resp = client.post("/auth/signup", data=signup_payload, follow_redirects=True)
    assert signup_resp.status_code == 200

    # 2. Log in with the same client
    login_payload = {
        "email": "session.tester@example.com",
        "password": "Password123!",
    }
    login_resp = client.post("/auth/login", data=login_payload, follow_redirects=True)
    assert login_resp.status_code == 200

    # Ensure g._login_user cache is cleared so subsequent requests actively exercise load_user
    g.pop("_login_user", None)

    # 3. Request '/', '/topics/', and topic page using the SAME client (session cookie kept)
    resp_home = client.get("/")
    assert resp_home.status_code == 200
    assert b"Browse Semester 5 Notes" in resp_home.data

    g.pop("_login_user", None)
    resp_topics = client.get("/topics/")
    assert resp_topics.status_code == 200
    assert b"Semester 5 Subjects" in resp_topics.data

    g.pop("_login_user", None)
    resp_topic = client.get(f"/topics/{topic_id}")
    assert resp_topic.status_code == 200
    assert b"Virtual Memory" in resp_topic.data
    assert b"Paging architecture." in resp_topic.data


def test_user_loader_deleted_or_invalid_user_session(client: FlaskClient, app):
    """Regression test: invalid or deleted user in session cookie does not crash and is treated as logged out."""
    with app.app_context():
        temp_user = User(
            name="Disposable User",
            email="disposable@example.com",
            semester=3,
        )
        temp_user.set_password("TempPassword123!")
        db.session.add(temp_user)
        db.session.commit()
        temp_user_id = temp_user.id

    # Log in so session cookie is set
    login_resp = client.post(
        "/auth/login",
        data={
            "email": "disposable@example.com",
            "password": "TempPassword123!",
        },
        follow_redirects=True,
    )
    assert login_resp.status_code == 200

    # Delete the user from the database while session cookie remains in client
    with app.app_context():
        user_to_delete = db.session.get(User, temp_user_id)
        assert user_to_delete is not None
        db.session.delete(user_to_delete)
        db.session.commit()

    # Clear request/app context cache so load_user executes against DB for the deleted user
    g.pop("_login_user", None)

    # Protected page should not crash with 500 or AttributeError, but safely redirect to login
    resp_protected = client.get("/topics/")
    assert resp_protected.status_code == 302
    assert "/auth/login" in resp_protected.headers["Location"]

    # Public page should return 200 and treat user as anonymous/logged-out
    g.pop("_login_user", None)
    resp_home = client.get("/")
    assert resp_home.status_code == 200
    assert b"Sign In to Account" in resp_home.data

    # Also test completely malformed non-integer user_id in session cookie
    with client.session_transaction() as sess:
        sess["_user_id"] = "invalid_non_numeric_id"

    g.pop("_login_user", None)
    resp_malformed = client.get("/topics/")
    assert resp_malformed.status_code == 302
    assert "/auth/login" in resp_malformed.headers["Location"]

