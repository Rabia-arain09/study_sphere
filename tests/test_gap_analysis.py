"""Comprehensive unit and integration tests for prerequisite gap analysis (Phase 6).

Covers:
- Chain A <- B <- C where C is weak (B weak, A not attempted, expected order A then B)
- Good prerequisites are skipped but their own weak prerequisites are still found
- Cycle safety in prerequisite traversal
- Depth limit (max depth 4)
- 10-item limit
- Ordering ties: depth descending, then difficulty ascending, then week ascending
- User isolation: student only sees gaps computed from own attempts
- Login required on /topics/<id>/revise and /topics/<id>/revise.json
- Unknown topic returns 404
- Friendly empty-gap message when all prerequisites are mastered
- Informative message when topic has no prerequisites
- "Revise these first" card shown only for Weak attempts (on result & topic pages)
- JSON shape on /topics/<id>/revise.json
- Query count constant (<= 4 queries) independent of graph size
"""

from __future__ import annotations

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import event

from app.extensions import db
from app.models.attempt import Attempt, MasteryLabel
from app.models.course import Course
from app.models.prerequisite import Prerequisite
from app.models.topic import Topic
from app.models.user import User
from app.services.gap_analysis import (
    GapList,
    get_prerequisite_gaps,
    build_prerequisite_graph,
    traverse_prerequisites_bfs,
)


@pytest.fixture
def gap_course(app: Flask) -> Course:
    """Create and persist a test Course model."""
    with app.app_context():
        course = Course(
            code="CS-TEST",
            title="Computer Science Core",
            semester=5,
            domain="Computing Core",
            credit_hours=3,
            contact_hours="3-0-0",
        )
        db.session.add(course)
        db.session.commit()
        return db.session.get(Course, course.id)


def _make_topic(
    course_id: int,
    name: str,
    difficulty: int = 1,
    week: str | None = None,
    semester: int = 5,
    subject: str = "Computer Science Core",
) -> Topic:
    """Helper to create and persist a Topic."""
    topic = Topic(
        course_id=course_id,
        name=name,
        difficulty=difficulty,
        week=week,
        semester=semester,
        subject=subject,
        content=f"Lecture notes for {name}",
    )
    db.session.add(topic)
    db.session.commit()
    return topic


def _make_prereq(topic_id: int, prereq_id: int) -> Prerequisite:
    """Helper to link topic_id requiring prereq_id."""
    prereq = Prerequisite(topic_id=topic_id, prerequisite_topic_id=prereq_id)
    db.session.add(prereq)
    db.session.commit()
    return prereq


def _make_attempt(
    user_id: int,
    topic_id: int,
    label: MasteryLabel,
    score: float = 1.0,
    total_questions: int = 4,
    attempt_number: int = 1,
) -> Attempt:
    """Helper to record an attempt for a user and topic."""
    att = Attempt(
        user_id=user_id,
        topic_id=topic_id,
        score=score,
        total_questions=total_questions,
        wrong_count=total_questions - score,
        attempt_number=attempt_number,
        label=label,
    )
    db.session.add(att)
    db.session.commit()
    return att


# ============================================================================
# 1. Chain A <- B <- C where C is weak (B weak, A not attempted, order A then B)
# ============================================================================
def test_chain_ordering(app: Flask, gap_course: Course, test_user: User):
    """Verify chain A <- B <- C where C is weak returns order [A, B] (deeper first)."""
    with app.app_context():
        # Setup topics
        topic_a = _make_topic(gap_course.id, "Topic A", difficulty=2, week="1")
        topic_b = _make_topic(gap_course.id, "Topic B", difficulty=2, week="2")
        topic_c = _make_topic(gap_course.id, "Topic C", difficulty=2, week="3")

        # C requires B; B requires A
        _make_prereq(topic_c.id, topic_b.id)
        _make_prereq(topic_b.id, topic_a.id)

        # User attempts C (Weak) and B (Weak); A is not attempted
        _make_attempt(test_user.id, topic_c.id, label=MasteryLabel.WEAK, score=1.0)
        _make_attempt(test_user.id, topic_b.id, label=MasteryLabel.WEAK, score=1.5)

        gaps = get_prerequisite_gaps(topic_c.id, test_user.id)

        assert isinstance(gaps, list)
        assert len(gaps) == 2

        # Expected order: A (depth 2) then B (depth 1)
        assert gaps[0]["topic_id"] == topic_a.id
        assert gaps[0]["name"] == "Topic A"
        assert gaps[0]["status"] == "Not attempted"
        assert gaps[0]["depth"] == 2
        assert gaps[0]["latest_percentage"] is None

        assert gaps[1]["topic_id"] == topic_b.id
        assert gaps[1]["name"] == "Topic B"
        assert gaps[1]["status"] == "Weak"
        assert gaps[1]["depth"] == 1
        assert gaps[1]["latest_percentage"] == round((1.5 / 4.0) * 100.0, 1)


# ============================================================================
# 2. Good prerequisites are skipped but their own weak prerequisites are found
# ============================================================================
def test_good_prerequisites_skipped_but_subprerequisites_found(
    app: Flask, gap_course: Course, test_user: User
):
    """Verify Good prerequisites are not gaps, but BFS walk continues through them."""
    with app.app_context():
        topic_a = _make_topic(gap_course.id, "Foundation A", difficulty=1, week="1")
        topic_b = _make_topic(gap_course.id, "Intermediate B", difficulty=2, week="2")
        topic_c = _make_topic(gap_course.id, "Target C", difficulty=3, week="3")

        _make_prereq(topic_c.id, topic_b.id)
        _make_prereq(topic_b.id, topic_a.id)

        # C is Weak, B is Good (mastered), A is Weak
        _make_attempt(test_user.id, topic_c.id, label=MasteryLabel.WEAK, score=1.0)
        _make_attempt(test_user.id, topic_b.id, label=MasteryLabel.GOOD, score=3.0)
        _make_attempt(test_user.id, topic_a.id, label=MasteryLabel.WEAK, score=1.0)

        gaps = get_prerequisite_gaps(topic_c.id, test_user.id)

        # B is skipped as it is Good, but A is found and included!
        assert len(gaps) == 1
        assert gaps[0]["topic_id"] == topic_a.id
        assert gaps[0]["name"] == "Foundation A"
        assert gaps[0]["status"] == "Weak"
        assert gaps[0]["depth"] == 2


# ============================================================================
# 3. Cycle safety
# ============================================================================
def test_cycle_safety(app: Flask, gap_course: Course, test_user: User):
    """Verify graph traversal handles cycles safely using visited set without infinite loops."""
    with app.app_context():
        t1 = _make_topic(gap_course.id, "Cycle T1")
        t2 = _make_topic(gap_course.id, "Cycle T2")
        t3 = _make_topic(gap_course.id, "Cycle T3")

        # Create directed cycle: T1 -> T2 -> T3 -> T2
        _make_prereq(t1.id, t2.id)
        _make_prereq(t2.id, t3.id)
        _make_prereq(t3.id, t2.id)

        # Traversal from T1 should terminate cleanly
        depths = traverse_prerequisites_bfs(
            t1.id, {t1.id: [t2.id], t2.id: [t3.id], t3.id: [t2.id]}
        )
        assert t2.id in depths
        assert t3.id in depths
        assert len(depths) == 2

        gaps = get_prerequisite_gaps(t1.id, test_user.id)
        assert len(gaps) == 2


# ============================================================================
# 4. Depth limit (max depth 4)
# ============================================================================
def test_depth_limit(app: Flask, gap_course: Course, test_user: User):
    """Verify traversal strictly bounds walk back to max depth 4."""
    with app.app_context():
        # Chain of 6 topics: C -> D1 -> D2 -> D3 -> D4 -> D5
        topics = [_make_topic(gap_course.id, f"Depth Node {i}") for i in range(6)]
        for i in range(5):
            _make_prereq(topics[i].id, topics[i + 1].id)

        gaps = get_prerequisite_gaps(topics[0].id, test_user.id, max_depth=4)

        # Depths visited must be 1, 2, 3, 4 (4 nodes total); depth 5 excluded
        gap_ids = [g["topic_id"] for g in gaps]
        assert topics[1].id in gap_ids  # depth 1
        assert topics[2].id in gap_ids  # depth 2
        assert topics[3].id in gap_ids  # depth 3
        assert topics[4].id in gap_ids  # depth 4
        assert topics[5].id not in gap_ids  # depth 5 omitted!
        assert len(gaps) == 4


# ============================================================================
# 5. 10-item limit
# ============================================================================
def test_ten_item_limit(app: Flask, gap_course: Course, test_user: User):
    """Verify result list is strictly capped at 10 items even when more gaps exist."""
    with app.app_context():
        target = _make_topic(gap_course.id, "Target Hub")
        prereqs = [_make_topic(gap_course.id, f"Prereq Hub {i}") for i in range(15)]
        for p in prereqs:
            _make_prereq(target.id, p.id)

        gaps = get_prerequisite_gaps(target.id, test_user.id)
        assert len(gaps) == 10


# ============================================================================
# 6. Ordering ties: depth descending, difficulty ascending, week ascending
# ============================================================================
def test_ordering_ties(app: Flask, gap_course: Course, test_user: User):
    """Verify ties at the same depth sort by difficulty (easier first) then week (earlier first)."""
    with app.app_context():
        target = _make_topic(gap_course.id, "Target Topic")

        # Deeper prerequisite (depth 2)
        mid = _make_topic(gap_course.id, "Mid Topic", difficulty=3, week="4")
        deep = _make_topic(gap_course.id, "Deep Topic", difficulty=5, week="10")
        _make_prereq(target.id, mid.id)
        _make_prereq(mid.id, deep.id)

        # Same depth (depth 1) with varying difficulty and week
        # p1: diff 1, week 3
        # p2: diff 1, week 1
        # p3: diff 2, week 1
        p1 = _make_topic(gap_course.id, "Prereq 1", difficulty=1, week="3")
        p2 = _make_topic(gap_course.id, "Prereq 2", difficulty=1, week="1")
        p3 = _make_topic(gap_course.id, "Prereq 3", difficulty=2, week="1")
        _make_prereq(target.id, p1.id)
        _make_prereq(target.id, p2.id)
        _make_prereq(target.id, p3.id)

        gaps = get_prerequisite_gaps(target.id, test_user.id)

        # Deep (depth 2) must come first
        assert gaps[0]["topic_id"] == deep.id

        # At depth 1:
        # p2 (diff 1, week 1) before p1 (diff 1, week 3)
        # p1 (diff 1, week 3) before p3 (diff 2, week 1)
        depth1_ids = [g["topic_id"] for g in gaps[1:]]
        assert depth1_ids.index(p2.id) < depth1_ids.index(p1.id)
        assert depth1_ids.index(p1.id) < depth1_ids.index(p3.id)


# ============================================================================
# 7. User isolation
# ============================================================================
def test_user_isolation(app: Flask, gap_course: Course, test_user: User):
    """Verify that gaps are computed strictly from the requesting user's attempts."""
    with app.app_context():
        target = _make_topic(gap_course.id, "Isolation Target")
        prereq = _make_topic(gap_course.id, "Isolation Prereq")
        _make_prereq(target.id, prereq.id)

        # Create user 2
        user2 = User(name="Other Student", email="other@example.com", semester=5)
        user2.set_password("Password123")
        db.session.add(user2)
        db.session.commit()

        # User 1 has a WEAK attempt on prereq
        _make_attempt(test_user.id, prereq.id, label=MasteryLabel.WEAK, score=1.0)

        # User 2 has an EXCELLENT attempt on prereq
        _make_attempt(user2.id, prereq.id, label=MasteryLabel.EXCELLENT, score=4.0)

        # User 1 should see prereq as a gap with Weak status
        gaps1 = get_prerequisite_gaps(target.id, test_user.id)
        assert len(gaps1) == 1
        assert gaps1[0]["topic_id"] == prereq.id
        assert gaps1[0]["status"] == "Weak"

        # User 2 should NOT see prereq as a gap (it was Excellent)
        gaps2 = get_prerequisite_gaps(target.id, user2.id)
        assert len(gaps2) == 0
        assert gaps2.has_prerequisites is True


# ============================================================================
# 8. Login required
# ============================================================================
def test_login_required(client: FlaskClient, gap_course: Course):
    """Verify /topics/<id>/revise and /topics/<id>/revise.json require authentication."""
    topic = _make_topic(gap_course.id, "Auth Test Topic")

    # Unauthenticated GET /topics/<id>/revise -> redirect to login (302)
    res_page = client.get(f"/topics/{topic.id}/revise")
    assert res_page.status_code == 302
    assert "/auth/login" in res_page.headers.get("Location", "")

    # Unauthenticated GET /topics/<id>/revise.json -> redirect to login (302)
    res_json = client.get(f"/topics/{topic.id}/revise.json")
    assert res_json.status_code == 302


# ============================================================================
# 9. Unknown topic 404
# ============================================================================
def test_unknown_topic_404(auth_client: FlaskClient):
    """Verify non-existent topic ID returns 404 on both HTML and JSON endpoints."""
    res_html = auth_client.get("/topics/999999/revise")
    assert res_html.status_code == 404

    res_json = auth_client.get("/topics/999999/revise.json")
    assert res_json.status_code == 404


# ============================================================================
# 10. Friendly empty-gap message
# ============================================================================
def test_empty_gap_message(
    auth_client: FlaskClient, gap_course: Course, test_user: User
):
    """Verify friendly message is rendered when topic has prerequisites but none are gaps."""
    target = _make_topic(gap_course.id, "Target All Good")
    prereq = _make_topic(gap_course.id, "Prereq All Good")
    _make_prereq(target.id, prereq.id)

    # Student scored Excellent on prerequisite
    _make_attempt(test_user.id, prereq.id, label=MasteryLabel.EXCELLENT, score=4.0)

    res = auth_client.get(f"/topics/{target.id}/revise")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # Required verbatim string check
    assert (
        "Your prerequisites look fine. Review this topic's notes and retake the quiz."
        in html
    )


# ============================================================================
# 11. No-prerequisite message
# ============================================================================
def test_no_prerequisite_message(auth_client: FlaskClient, gap_course: Course):
    """Verify message stating topic has no prerequisites when topic has no prerequisite edges."""
    root_topic = _make_topic(gap_course.id, "Root Foundational Concept")

    res = auth_client.get(f"/topics/{root_topic.id}/revise")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    assert "This topic has no prerequisites" in html


# ============================================================================
# 12. "Revise these first" card shown only for Weak
# ============================================================================
def test_card_shown_only_for_weak(
    auth_client: FlaskClient, gap_course: Course, test_user: User
):
    """Verify the 'Revise these first' card appears on result and topic pages only when mastery is Weak."""
    topic = _make_topic(gap_course.id, "Card Test Topic")
    prereq = _make_topic(gap_course.id, "Card Test Prereq")
    _make_prereq(topic.id, prereq.id)

    # 1. Take quiz with Weak attempt
    weak_att = _make_attempt(
        test_user.id, topic.id, label=MasteryLabel.WEAK, score=1.0, attempt_number=1
    )

    # Result page: card must appear
    res_weak = auth_client.get(f"/quiz/attempt/{weak_att.id}")
    assert res_weak.status_code == 200
    html_weak = res_weak.get_data(as_text=True)
    assert "Revise these first" in html_weak
    assert "See full list" in html_weak

    # Topic detail page: latest attempt is Weak, so card must appear
    res_topic_weak = auth_client.get(f"/topics/{topic.id}")
    assert res_topic_weak.status_code == 200
    assert "Revise these first" in res_topic_weak.get_data(as_text=True)

    # 2. Add an Excellent attempt (superseding the Weak attempt)
    good_att = _make_attempt(
        test_user.id,
        topic.id,
        label=MasteryLabel.EXCELLENT,
        score=4.0,
        attempt_number=2,
    )

    # Result page for Excellent attempt: card must NOT appear
    res_good = auth_client.get(f"/quiz/attempt/{good_att.id}")
    assert res_good.status_code == 200
    html_good = res_good.get_data(as_text=True)
    assert "Revise these first" not in html_good

    # Topic detail page: latest attempt is Excellent, so card must NOT appear
    res_topic_good = auth_client.get(f"/topics/{topic.id}")
    assert res_topic_good.status_code == 200
    assert "Revise these first" not in res_topic_good.get_data(as_text=True)


# ============================================================================
# 13. JSON shape
# ============================================================================
def test_json_shape(auth_client: FlaskClient, gap_course: Course, test_user: User):
    """Verify GET /topics/<id>/revise.json returns list of gap objects with exact keys."""
    target = _make_topic(gap_course.id, "JSON Target")
    prereq = _make_topic(gap_course.id, "JSON Prereq")
    _make_prereq(target.id, prereq.id)

    _make_attempt(test_user.id, prereq.id, label=MasteryLabel.WEAK, score=2.0)

    res = auth_client.get(f"/topics/{target.id}/revise.json")
    assert res.status_code == 200
    assert res.is_json

    data = res.get_json()
    assert isinstance(data, list)
    assert len(data) == 1

    item = data[0]
    required_keys = {
        "topic_id",
        "id",
        "name",
        "course_name",
        "status",
        "depth",
        "latest_percentage",
    }
    assert required_keys.issubset(item.keys())
    assert item["topic_id"] == prereq.id
    assert item["name"] == "JSON Prereq"
    assert item["status"] == "Weak"
    assert item["depth"] == 1
    assert item["latest_percentage"] == 50.0


# ============================================================================
# 14. Query count constant when topics/edges grow
# ============================================================================
def test_query_count_constant(app: Flask, gap_course: Course, test_user: User):
    """Verify that get_prerequisite_gaps runs in constant (<= 4) queries regardless of graph size."""
    with app.app_context():
        # Setup small graph: Target -> P1 -> P2
        target_small = _make_topic(gap_course.id, "Query Small Target")
        p1 = _make_topic(gap_course.id, "Query Small P1")
        p2 = _make_topic(gap_course.id, "Query Small P2")
        _make_prereq(target_small.id, p1.id)
        _make_prereq(p1.id, p2.id)
        _make_attempt(test_user.id, p1.id, label=MasteryLabel.WEAK, score=1.0)

        # Setup larger graph: Target -> 12 prerequisites
        target_large = _make_topic(gap_course.id, "Query Large Target")
        for i in range(12):
            large_p = _make_topic(gap_course.id, f"Query Large P{i}")
            _make_prereq(target_large.id, large_p.id)
            if i % 2 == 0:
                _make_attempt(
                    test_user.id, large_p.id, label=MasteryLabel.WEAK, score=1.0
                )

        target_small_id = int(target_small.id)
        target_large_id = int(target_large.id)
        user_id = int(test_user.id)

        captured_queries: list[str] = []

        def capture_query(conn, cursor, statement, parameters, context, executemany):
            captured_queries.append(statement)

        event.listen(db.engine, "before_cursor_execute", capture_query)
        try:
            # Measure small graph
            captured_queries.clear()
            get_prerequisite_gaps(target_small_id, user_id)
            small_count = len(captured_queries)

            # Measure large graph
            captured_queries.clear()
            get_prerequisite_gaps(target_large_id, user_id)
            large_count = len(captured_queries)

            # Both must be at most 3 queries inside the service (at most 4 queries overall)
            assert small_count <= 3
            assert large_count <= 3
            # And query count must not increase with graph size!
            assert small_count == large_count
        finally:
            event.remove(db.engine, "before_cursor_execute", capture_query)
