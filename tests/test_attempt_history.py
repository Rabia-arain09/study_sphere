"""Unit and integration tests for quiz attempt history features."""

from __future__ import annotations

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import event
from app.extensions import db
from app.models.attempt import Attempt, MasteryLabel
from app.models.course import Course
from app.models.question import Question, QuestionType, QuestionSource
from app.models.topic import Topic
from app.models.user import User
from app.services.quiz_engine import calculate_attempts_history


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def history_setup(app: Flask, test_user: User) -> dict[str, int]:
    """Create a course and two topics for attempt history testing."""
    with app.app_context():
        course = Course(
            code="CS401",
            title="Advanced Algorithms",
            semester=5,
            domain="Computer Science",
            credit_hours=3,
            contact_hours="3-0-3",
        )
        db.session.add(course)
        db.session.flush()

        topic1 = Topic(
            course_id=course.id,
            name="Dynamic Programming",
            semester=5,
            subject="Advanced Algorithms",
            week="Week 4",
            difficulty=4,
            content="## Dynamic Programming\n\nOptimal substructure and memoization.",
            content_reviewed=True,
        )
        topic2 = Topic(
            course_id=course.id,
            name="Graph Algorithms",
            semester=5,
            subject="Advanced Algorithms",
            week="Week 5",
            difficulty=3,
            content="## Graph Algorithms\n\nBreadth-first and depth-first search.",
            content_reviewed=True,
        )
        db.session.add_all([topic1, topic2])
        db.session.flush()

        # Add questions so topic quiz pages function
        q1 = Question(
            topic_id=topic1.id,
            type=QuestionType.MCQ,
            question_text="What is the time complexity of 0/1 knapsack using DP?",
            options={"A": "O(nW)", "B": "O(2^n)", "C": "O(n log n)", "D": "O(n)"},
            correct_answer="A",
            source=QuestionSource.GENERATED,
        )
        db.session.add(q1)
        db.session.commit()

        return {
            "course_id": course.id,
            "topic1_id": topic1.id,
            "topic2_id": topic2.id,
        }


# ==============================================================================
# 1. Topic Page Attempts Table & "View all" Link Tests
# ==============================================================================


def test_topic_page_empty_when_no_attempts(
    auth_client: FlaskClient,
    history_setup: dict[str, int],
) -> None:
    """Verify topic page shows clean empty state and Take Quiz button when 0 attempts exist."""
    topic_id = history_setup["topic1_id"]
    resp = auth_client.get(f"/topics/{topic_id}")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")

    assert "Take Quiz" in html
    assert "No attempts yet" in html
    assert "Your attempts" not in html
    assert "View all attempts" not in html


def test_topic_page_shows_up_to_5_attempts_and_view_all_link_only_when_needed(
    auth_client: FlaskClient,
    history_setup: dict[str, int],
    app: Flask,
    test_user: User,
) -> None:
    """Verify topic page renders up to 5 latest attempts and conditionally displays 'View all'."""
    topic_id = history_setup["topic1_id"]

    # 1. Seed 3 attempts: table visible, but "View all attempts" should NOT appear
    with app.app_context():
        for i in range(1, 4):
            att = Attempt(
                user_id=test_user.id,
                topic_id=topic_id,
                score=float(i),
                total_questions=4,
                wrong_count=float(4 - i),
                attempt_number=i,
                label=MasteryLabel.GOOD,
            )
            db.session.add(att)
        db.session.commit()

    resp3 = auth_client.get(f"/topics/{topic_id}")
    assert resp3.status_code == 200
    html3 = resp3.data.decode("utf-8")

    assert "Your attempts" in html3
    assert "#1" in html3
    assert "#2" in html3
    assert "#3" in html3
    assert "View all attempts" not in html3
    assert "Take Quiz" in html3

    # 2. Add 3 more attempts (total = 6): only latest 5 should be displayed (#6 to #2), #1 omitted
    with app.app_context():
        for i in range(4, 7):
            att = Attempt(
                user_id=test_user.id,
                topic_id=topic_id,
                score=float(i % 4 + 1),
                total_questions=4,
                wrong_count=float(4 - (i % 4 + 1)),
                attempt_number=i,
                label=MasteryLabel.BETTER,
            )
            db.session.add(att)
        db.session.commit()

    resp6 = auth_client.get(f"/topics/{topic_id}")
    assert resp6.status_code == 200
    html6 = resp6.data.decode("utf-8")

    assert "Your attempts" in html6
    assert "#6" in html6
    assert "#5" in html6
    assert "#4" in html6
    assert "#3" in html6
    assert "#2" in html6
    # Earliest attempt (#1) should not be in the top-5 table
    # (Checking within the table rows)
    assert "View all attempts" in html6
    assert f"/quiz/topic/{topic_id}/history" in html6


# ==============================================================================
# 2. Authentication Protection Tests
# ==============================================================================


def test_history_routes_require_login(
    client: FlaskClient,
    history_setup: dict[str, int],
) -> None:
    """Verify /quiz/history and /quiz/topic/<id>/history redirect unauthenticated users to login."""
    topic_id = history_setup["topic1_id"]

    r1 = client.get("/quiz/history")
    assert r1.status_code == 302
    assert "/auth/login" in r1.headers["Location"]

    r2 = client.get(f"/quiz/topic/{topic_id}/history")
    assert r2.status_code == 302
    assert "/auth/login" in r2.headers["Location"]


# ==============================================================================
# 3. User Isolation Tests (Users only see their own attempts)
# ==============================================================================


def test_user_isolation_on_history_pages(
    history_setup: dict[str, int],
    app: Flask,
    test_user: User,
) -> None:
    """Verify that User B cannot see attempts created by User A on any history view."""
    topic_id = history_setup["topic1_id"]

    # 1. Create attempts for test_user (User A)
    with app.app_context():
        att_a = Attempt(
            user_id=test_user.id,
            topic_id=topic_id,
            score=4.0,
            total_questions=4,
            wrong_count=0.0,
            attempt_number=1,
            label=MasteryLabel.EXCELLENT,
        )
        db.session.add(att_a)

        # 2. Create another user (User B)
        other_user = User(
            name="Alice Candidate",
            email="alice@example.com",
            semester=5,
        )
        other_user.set_password("AliceSecurePass1!")
        db.session.add(other_user)
        db.session.commit()

    # 3. Log in as other_user (User B)
    client_b = app.test_client()
    login_resp = client_b.post(
        "/auth/login",
        data={"email": "alice@example.com", "password": "AliceSecurePass1!"},
        follow_redirects=True,
    )
    assert login_resp.status_code == 200

    # User B checks topic history: should see 0 attempts
    r_topic_hist = client_b.get(f"/quiz/topic/{topic_id}/history")
    assert r_topic_hist.status_code == 200
    html_topic_hist = r_topic_hist.data.decode("utf-8")
    assert "No quiz attempts recorded yet" in html_topic_hist
    assert "0 Total Attempts" in html_topic_hist
    assert "Attempt #1" not in html_topic_hist

    # User B checks global history: should see 0 attempts
    r_global_hist = client_b.get("/quiz/history")
    assert r_global_hist.status_code == 200
    html_global_hist = r_global_hist.data.decode("utf-8")
    assert "No quiz history yet" in html_global_hist
    assert "Total Attempts</span>\n                <span class=\"metric-value font-bold\" style=\"font-size: 1.4rem; color: var(--neutral-800);\">0" in html_global_hist

    # User B checks topic page: should see empty attempts state
    r_topic_page = client_b.get(f"/topics/{topic_id}")
    assert r_topic_page.status_code == 200
    html_topic_page = r_topic_page.data.decode("utf-8")
    assert "No attempts yet" in html_topic_page
    assert "Your attempts" not in html_topic_page


# ==============================================================================
# 4. Empty States & 404 Tests
# ==============================================================================


def test_history_empty_states_and_404(
    auth_client: FlaskClient,
    history_setup: dict[str, int],
) -> None:
    """Verify friendly empty messages when 0 attempts and 404 for nonexistent topics."""
    topic_id = history_setup["topic1_id"]

    # Empty topic history
    r1 = auth_client.get(f"/quiz/topic/{topic_id}/history")
    assert r1.status_code == 200
    assert "No quiz attempts recorded yet" in r1.data.decode("utf-8")

    # Empty global history
    r2 = auth_client.get("/quiz/history")
    assert r2.status_code == 200
    assert "No quiz history yet" in r2.data.decode("utf-8")

    # 404 for unknown topic
    r3 = auth_client.get("/quiz/topic/999999/history")
    assert r3.status_code == 404


# ==============================================================================
# 5. Pagination Tests (/quiz/history)
# ==============================================================================


def test_quiz_history_pagination(
    auth_client: FlaskClient,
    history_setup: dict[str, int],
    app: Flask,
    test_user: User,
) -> None:
    """Verify /quiz/history paginates at 20 per page and safely handles invalid page parameters."""
    topic1_id = history_setup["topic1_id"]
    topic2_id = history_setup["topic2_id"]

    # Create 25 attempts (20 on page 1, 5 on page 2)
    with app.app_context():
        for i in range(1, 26):
            t_id = topic1_id if i % 2 == 1 else topic2_id
            att = Attempt(
                user_id=test_user.id,
                topic_id=t_id,
                score=3.0,
                total_questions=4,
                wrong_count=1.0,
                attempt_number=i,
                label=MasteryLabel.BETTER,
            )
            db.session.add(att)
        db.session.commit()

    # Page 1
    r_p1 = auth_client.get("/quiz/history?page=1")
    assert r_p1.status_code == 200
    html_p1 = r_p1.data.decode("utf-8")
    assert "Page 1 of 2" in html_p1
    assert "Next &rarr;" in html_p1
    assert "&larr; Previous" not in html_p1
    assert "Total Attempts</span>\n                <span class=\"metric-value font-bold\" style=\"font-size: 1.4rem; color: var(--neutral-800);\">25" in html_p1
    assert "Topics Attempted</span>\n                <span class=\"metric-value font-bold\" style=\"font-size: 1.4rem; color: var(--primary);\">2" in html_p1

    # Page 2
    r_p2 = auth_client.get("/quiz/history?page=2")
    assert r_p2.status_code == 200
    html_p2 = r_p2.data.decode("utf-8")
    assert "Page 2 of 2" in html_p2
    assert "&larr; Previous" in html_p2
    assert "Next &rarr;" not in html_p2

    # Invalid page parameter: string 'abc' -> defaults to page 1
    r_invalid = auth_client.get("/quiz/history?page=invalid_param")
    assert r_invalid.status_code == 200
    assert "Page 1 of 2" in r_invalid.data.decode("utf-8")

    # Negative page -> defaults to page 1
    r_neg = auth_client.get("/quiz/history?page=-5")
    assert r_neg.status_code == 200
    assert "Page 1 of 2" in r_neg.data.decode("utf-8")

    # Overflow page (page 999) -> clamps to page 2 (total_pages)
    r_over = auth_client.get("/quiz/history?page=999")
    assert r_over.status_code == 200
    assert "Page 2 of 2" in r_over.data.decode("utf-8")


# ==============================================================================
# 6. Change-Versus-Previous Delta Values Tests
# ==============================================================================


def test_change_versus_previous_deltas() -> None:
    """Verify pure-Python sequential score delta calculation for first, increasing, decreasing, and equal scores."""
    class MockAttempt:
        def __init__(self, att_id: int, attempt_num: int, score: float, total_q: int) -> None:
            self.id = att_id
            self.attempt_number = attempt_num
            self.score = score
            self.total_questions = total_q

    attempts = [
        MockAttempt(1, 1, 2.0, 4),   # 50.0% -> First attempt: change=None
        MockAttempt(2, 2, 3.0, 4),   # 75.0% -> Change = +25.0%
        MockAttempt(3, 3, 2.5, 4),   # 62.5% -> Change = -12.5%
        MockAttempt(4, 4, 2.5, 4),   # 62.5% -> Change = 0.0%
    ]

    history = calculate_attempts_history(attempts)
    # Output is newest first
    assert len(history) == 4

    # Latest attempt (#4): 62.5%, change = 0.0
    assert history[0].attempt.attempt_number == 4
    assert history[0].percentage == 62.5
    assert history[0].change == 0.0

    # Attempt #3: 62.5%, change = -12.5
    assert history[1].attempt.attempt_number == 3
    assert history[1].percentage == 62.5
    assert history[1].change == -12.5

    # Attempt #2: 75.0%, change = +25.0
    assert history[2].attempt.attempt_number == 2
    assert history[2].percentage == 75.0
    assert history[2].change == 25.0

    # First attempt (#1): 50.0%, change = None
    assert history[3].attempt.attempt_number == 1
    assert history[3].percentage == 50.0
    assert history[3].change is None


def test_change_rendered_with_directional_indicators(
    auth_client: FlaskClient,
    history_setup: dict[str, int],
    app: Flask,
    test_user: User,
) -> None:
    """Verify HTML renders up arrow, down arrow, equal, and em-dash for change values."""
    topic_id = history_setup["topic1_id"]

    with app.app_context():
        a1 = Attempt(user_id=test_user.id, topic_id=topic_id, score=2.0, total_questions=4, wrong_count=2.0, attempt_number=1, label=MasteryLabel.GOOD)
        a2 = Attempt(user_id=test_user.id, topic_id=topic_id, score=3.0, total_questions=4, wrong_count=1.0, attempt_number=2, label=MasteryLabel.BETTER)
        a3 = Attempt(user_id=test_user.id, topic_id=topic_id, score=1.0, total_questions=4, wrong_count=3.0, attempt_number=3, label=MasteryLabel.WEAK)
        a4 = Attempt(user_id=test_user.id, topic_id=topic_id, score=1.0, total_questions=4, wrong_count=3.0, attempt_number=4, label=MasteryLabel.WEAK)
        db.session.add_all([a1, a2, a3, a4])
        db.session.commit()

    resp = auth_client.get(f"/quiz/topic/{topic_id}/history")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")

    assert "↑ +25.0%" in html
    assert "↓ -50.0%" in html
    assert "= 0.0%" in html
    assert "—" in html


# ==============================================================================
# 7. Navbar Link Tests
# ==============================================================================


def test_navbar_history_link_visibility(
    app: Flask,
    test_user: User,
) -> None:
    """Verify History link appears in navbar for logged-in users and is hidden for guests."""
    # Anonymous visitor
    guest_client = app.test_client()
    r_guest = guest_client.get("/")
    assert r_guest.status_code == 200
    assert 'href="/quiz/history"' not in r_guest.data.decode("utf-8")
    assert "History</a>" not in r_guest.data.decode("utf-8")

    # Authenticated student
    auth_client = app.test_client()
    auth_client.post(
        "/auth/login",
        data={"email": test_user.email, "password": "SecurePassword123"},
        follow_redirects=True,
    )
    r_auth = auth_client.get("/")
    assert r_auth.status_code == 200
    assert 'href="/quiz/history"' in r_auth.data.decode("utf-8")
    assert "History</a>" in r_auth.data.decode("utf-8")


# ==============================================================================
# 8. Query Count Performance Tests (No N+1)
# ==============================================================================


def test_query_count_does_not_grow_with_attempts(
    app: Flask,
    test_user: User,
    history_setup: dict[str, int],
) -> None:
    """Verify database query count remains constant regardless of number of attempt records (no N+1)."""
    topic_id = history_setup["topic1_id"]

    client = app.test_client()
    client.post(
        "/auth/login",
        data={"email": test_user.email, "password": "TestPassword123!"},
        follow_redirects=True,
    )

    # 1. Measure query count with 2 attempts
    with app.app_context():
        for i in (1, 2):
            att = Attempt(
                user_id=test_user.id,
                topic_id=topic_id,
                score=float(i),
                total_questions=4,
                wrong_count=float(4 - i),
                attempt_number=i,
                label=MasteryLabel.GOOD,
            )
            db.session.add(att)
        db.session.commit()

    queries_2 = []

    def count_queries_2(conn, cursor, statement, parameters, context, executemany):
        queries_2.append(statement)

    event.listen(db.engine, "before_cursor_execute", count_queries_2)
    client.get("/quiz/history")
    client.get(f"/quiz/topic/{topic_id}/history")
    event.remove(db.engine, "before_cursor_execute", count_queries_2)

    count_at_2 = len(queries_2)

    # 2. Add 10 more attempts (total = 12 attempts)
    with app.app_context():
        for i in range(3, 13):
            att = Attempt(
                user_id=test_user.id,
                topic_id=topic_id,
                score=2.0,
                total_questions=4,
                wrong_count=2.0,
                attempt_number=i,
                label=MasteryLabel.GOOD,
            )
            db.session.add(att)
        db.session.commit()

    queries_12 = []

    def count_queries_12(conn, cursor, statement, parameters, context, executemany):
        queries_12.append(statement)

    event.listen(db.engine, "before_cursor_execute", count_queries_12)
    client.get("/quiz/history")
    client.get(f"/quiz/topic/{topic_id}/history")
    event.remove(db.engine, "before_cursor_execute", count_queries_12)

    count_at_12 = len(queries_12)

    # Query count must remain constant despite 6x increase in attempt records
    assert count_at_12 == count_at_2, (
        f"Query count grew with attempts! At 2: {count_at_2}, at 12: {count_at_12}"
    )
