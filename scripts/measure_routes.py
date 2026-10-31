"""Route performance and query counting measurement script for StudySphere against Supabase."""

from __future__ import annotations
import re
import sys
import time
from pathlib import Path
from typing import Any

# Ensure repository root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure Windows terminal handles UTF-8 safely
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy import event
from sqlalchemy.engine import Engine
from app import create_app
from app.extensions import db
from app.models.user import User

# Query capture state
_query_log: list[str] = []
_collecting: bool = False


@event.listens_for(Engine, "before_cursor_execute")
def count_sql_query(
    conn: Any,
    cursor: Any,
    statement: str,
    parameters: Any,
    context: Any,
    executemany: bool,
) -> None:
    """SQLAlchemy event listener tracking query count and statements during measurement."""
    global _collecting, _query_log
    if _collecting:
        _query_log.append(statement.strip())


def measure_supabase_routes() -> list[dict[str, Any]]:
    """Time target routes and count SQL queries per request with a temporary user."""
    global _collecting, _query_log
    app = create_app("development")

    routes_to_measure = [
        ("/", "Home page"),
        ("/topics/", "Semester picker (default)"),
        ("/topics/semester/5", "Semester 5 subjects"),
        ("/topics/course/23", "Course 23 topics"),
        ("/topics/1", "Topic 1 detail"),
    ]

    results: list[dict[str, Any]] = []

    with app.app_context():
        test_email = "temp_measure_perf@example.com"

        # 1. Clean up any leftover test user
        existing = User.query.filter_by(email=test_email).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()

        # 2. Create temporary test student in Supabase
        temp_user = User(
            name="Performance Measurement Student",
            email=test_email,
            semester=5,
        )
        temp_user.set_password("PerfTestPass123!")
        db.session.add(temp_user)
        db.session.commit()

        try:
            with app.test_client() as client:
                # 3. Authenticate session
                get_login = client.get("/auth/login")
                csrf_match = re.search(
                    r'name="csrf_token"\s+type="hidden"\s+value="([^"]+)"',
                    get_login.data.decode("utf-8", errors="replace"),
                ) or re.search(
                    r'value="([^"]+)"\s+name="csrf_token"',
                    get_login.data.decode("utf-8", errors="replace"),
                )
                assert csrf_match, "Failed to extract CSRF token"
                csrf_token = csrf_match.group(1)

                post_login = client.post(
                    "/auth/login",
                    data={
                        "csrf_token": csrf_token,
                        "email": test_email,
                        "password": "PerfTestPass123!",
                    },
                    follow_redirects=True,
                )
                assert post_login.status_code == 200, "Authentication failed"

                backend_label = (
                    "SQLite"
                    if db.engine.dialect.name == "sqlite"
                    else "Supabase (PostgreSQL)"
                )
                print("\n================================================================================")
                print(f" MEASURING ROUTES AGAINST {backend_label.upper()} (DATABASE_URL)")
                print("================================================================================")

                for path, desc in routes_to_measure:
                    _query_log.clear()
                    _collecting = True
                    start_time = time.perf_counter()

                    resp = client.get(path)

                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    _collecting = False
                    query_count = len(_query_log)

                    assert resp.status_code == 200, f"Route {path} returned {resp.status_code}"

                    result_item = {
                        "path": path,
                        "description": desc,
                        "status_code": resp.status_code,
                        "time_ms": elapsed_ms,
                        "query_count": query_count,
                        "queries": list(_query_log),
                    }
                    results.append(result_item)

                    print(f"Route: {path:20} | Status: {resp.status_code} | Time: {elapsed_ms:8.2f} ms | Queries: {query_count:3d}")

                print("================================================================================\n")

        finally:
            # Clean up temporary user
            _collecting = False
            backend_name = (
                "SQLite"
                if db.engine.dialect.name == "sqlite"
                else "Supabase"
            )
            user_cleanup = User.query.filter_by(email=test_email).first()
            if user_cleanup:
                db.session.delete(user_cleanup)
                db.session.commit()
                print(f"[OK] Temporary measurement user cleanly deleted from {backend_name}.")

    return results


if __name__ == "__main__":
    measure_supabase_routes()
