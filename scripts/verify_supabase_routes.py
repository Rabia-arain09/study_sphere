"""Verification script testing routes against Supabase PostgreSQL database with a single session."""

from __future__ import annotations
import re
import sys
from pathlib import Path

# Ensure repository root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure Windows terminal handles UTF-8 safely
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app import create_app
from app.extensions import db
from app.models.user import User


def verify_supabase_session_routes() -> None:
    """Verify live Supabase routes in a single authenticated session using a temporary user."""
    app = create_app("development")

    with app.app_context():
        test_email = "temp_verify_session_fix@example.com"

        # 1. Clean up any previous test artifact
        existing = User.query.filter_by(email=test_email).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()

        # 2. Create temporary test student in Supabase
        temp_user = User(
            name="Supabase Session Verifier",
            email=test_email,
            semester=5,
        )
        temp_user.set_password("SessionVerify123!")
        db.session.add(temp_user)
        db.session.commit()
        print("[OK] Created temporary verification user in Supabase.")

        try:
            with app.test_client() as client:
                # 3. Obtain CSRF token from login form
                get_login = client.get("/auth/login")
                assert get_login.status_code == 200, f"Expected 200 on GET /auth/login, got {get_login.status_code}"

                csrf_match = re.search(
                    r'name="csrf_token"\s+type="hidden"\s+value="([^"]+)"',
                    get_login.data.decode("utf-8", errors="replace"),
                )
                if not csrf_match:
                    csrf_match = re.search(
                        r'value="([^"]+)"\s+name="csrf_token"',
                        get_login.data.decode("utf-8", errors="replace"),
                    )
                assert csrf_match is not None, "CSRF token not found in login form"
                csrf_token = csrf_match.group(1)

                # 4. Authenticate session
                post_login = client.post(
                    "/auth/login",
                    data={
                        "csrf_token": csrf_token,
                        "email": test_email,
                        "password": "SessionVerify123!",
                    },
                    follow_redirects=True,
                )
                assert post_login.status_code == 200, f"Expected 200 on login follow_redirects, got {post_login.status_code}"
                assert b"Logout" in post_login.data, "Session authentication failed (Logout link missing)"
                print("[OK] Authenticated session established successfully.")

                # 5. Check required routes in the same session
                routes_to_verify = [
                    ("/", "Home landing page"),
                    ("/topics/", "Semester picker (defaults to Sem 5)"),
                    ("/topics/semester/5", "Semester 5 subjects list"),
                    ("/topics/course/23", "Course 23 topics (Operating Systems)"),
                    ("/topics/1", "Topic 1 notes reader"),
                ]

                print("\n" + "=" * 70)
                print(" SUPABASE SINGLE-SESSION ROUTE VERIFICATION")
                print("=" * 70)

                for path, desc in routes_to_verify:
                    resp = client.get(path)
                    assert resp.status_code == 200, f"Route {path} returned {resp.status_code}, expected 200"
                    print(f"  [OK] 200  {path:25} -> {desc}")

                print("=" * 70)
                print(" All 5 target routes returned 200 for the logged-in user!")
                print("=" * 70)

        finally:
            # 6. Delete temporary test user
            user_cleanup = User.query.filter_by(email=test_email).first()
            if user_cleanup:
                db.session.delete(user_cleanup)
                db.session.commit()
                print("[OK] Deleted temporary verification user from Supabase.")


if __name__ == "__main__":
    verify_supabase_session_routes()
