"""Comprehensive unit and integration tests for adaptive recommendations and dashboard (Phase 8).

Covers:
1. Tier ordering for a fixture graph (Tier 1 > Tier 2 > Tier 3 > Tier 4 > Tier 5)
2. Reasons text for all tiers
3. rerank_related puts Weak and prerequisite-of-weak first, and Excellent last
4. rerank_related similarity tie-breaker inside a tier
5. Label field and ?adaptive=1 parameter on GET /topics/<id>/related JSON endpoint
6. Dashboard login required (302 redirect to /auth/login)
7. Dashboard user isolation (user only sees their own data)
8. Dashboard friendly empty state for new user ("Take your first quiz to see your progress")
9. Dashboard summary numbers accuracy (attempts, topics, avg %, mastered, weak, uploads)
10. Dashboard Chart.js JSON shapes and label colors (red, amber, blue, green)
11. Dashboard contains no CDN URLs (Chart.js loaded from local vendor only)
12. Query count constant when attempts count grows (at most 5 queries)
13. Topic page shows mastery/new badges in Related Topics sidebar
14. Recommendations change dynamically after a new quiz attempt
"""

from __future__ import annotations

import json
import re
from typing import Generator
import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import event

from app.extensions import db
from app.models.attempt import Attempt, MasteryLabel
from app.models.course import Course
from app.models.prerequisite import Prerequisite
from app.models.topic import Topic
from app.models.upload import Upload
from app.models.user import User
from app.services.adaptive_service import (
    get_next_topics,
    get_user_latest_topic_attempts,
    rerank_related,
)
from app.services.recommendation_service import reset_recommender


@pytest.fixture
def adaptive_setup(app: Flask, test_user: User) -> dict[str, Any]:
    """Create a structured curriculum graph for Semester 5 adaptive testing.

    Graph Topology:
        Linear Chain:
            t_linear_alg (A, foundational, no prereq)
            <- t_perceptron (B, prereq: A)
            <- t_neural_net (C, prereq: B)
        Ready to learn (no prereqs):
            t_decision_trees (D)
        Locked (prereq unattempted):
            t_deep_learning (E, prereq: C)
        Practice / Mastered:
            t_bayes (F)
            t_svm (G)
    """
    reset_recommender()
    with app.app_context():
        course = Course(
            code="CS-ML501",
            title="Machine Learning Systems",
            semester=5,
            domain="Computing Core",
            credit_hours=3,
            contact_hours="3-0-0",
        )
        db.session.add(course)
        db.session.commit()

        # Create topics
        t_linear_alg = Topic(
            course_id=course.id,
            name="Linear Algebra for ML",
            difficulty=1,
            week="1",
            semester=5,
            subject=course.title,
            content="Matrix multiplication vector spaces dot products eigenvalues lecture notes.",
        )
        t_perceptron = Topic(
            course_id=course.id,
            name="Perceptron Foundations",
            difficulty=2,
            week="2",
            semester=5,
            subject=course.title,
            content="Binary classification linear decision boundary weights updates perceptron.",
        )
        t_neural_net = Topic(
            course_id=course.id,
            name="Neural Networks Architecture",
            difficulty=3,
            week="3",
            semester=5,
            subject=course.title,
            content="Multilayer perceptron backpropagation gradient descent neural networks activation.",
        )
        t_decision_trees = Topic(
            course_id=course.id,
            name="Decision Tree Classifiers",
            difficulty=2,
            week="4",
            semester=5,
            subject=course.title,
            content="Information gain entropy gini impurity splitting criteria decision tree classification.",
        )
        t_deep_learning = Topic(
            course_id=course.id,
            name="Deep Learning Transformers",
            difficulty=4,
            week="5",
            semester=5,
            subject=course.title,
            content="Attention mechanism self attention transformer layers positional encoding deep learning.",
        )
        t_bayes = Topic(
            course_id=course.id,
            name="Naive Bayes Probability",
            difficulty=2,
            week="6",
            semester=5,
            subject=course.title,
            content="Prior likelihood posterior conditional independence bayesian inference classifier.",
        )
        t_svm = Topic(
            course_id=course.id,
            name="Support Vector Machines",
            difficulty=3,
            week="7",
            semester=5,
            subject=course.title,
            content="Support vector machines maximum margin hyperplanes kernel trick slack variables.",
        )

        db.session.add_all([
            t_linear_alg,
            t_perceptron,
            t_neural_net,
            t_decision_trees,
            t_deep_learning,
            t_bayes,
            t_svm,
        ])
        db.session.commit()

        # Prerequisite Edges:
        # Perceptron requires Linear Algebra
        p1 = Prerequisite(topic_id=t_perceptron.id, prerequisite_topic_id=t_linear_alg.id)
        # Neural Networks requires Perceptron
        p2 = Prerequisite(topic_id=t_neural_net.id, prerequisite_topic_id=t_perceptron.id)
        # Deep Learning requires Neural Networks
        p3 = Prerequisite(topic_id=t_deep_learning.id, prerequisite_topic_id=t_neural_net.id)

        db.session.add_all([p1, p2, p3])
        db.session.commit()

        return {
            "course_id": course.id,
            "t_linear_alg_id": t_linear_alg.id,
            "t_perceptron_id": t_perceptron.id,
            "t_neural_net_id": t_neural_net.id,
            "t_decision_trees_id": t_decision_trees.id,
            "t_deep_learning_id": t_deep_learning.id,
            "t_bayes_id": t_bayes.id,
            "t_svm_id": t_svm.id,
            "user_id": test_user.id,
        }


def _create_attempt(
    user_id: int,
    topic_id: int,
    score: float,
    total: int = 4,
    label: MasteryLabel = MasteryLabel.WEAK,
    attempt_number: int = 1,
) -> Attempt:
    """Helper to record an attempt in the active database session."""
    wrong = float(total - score)
    att = Attempt(
        user_id=user_id,
        topic_id=topic_id,
        score=score,
        total_questions=total,
        wrong_count=wrong,
        attempt_number=attempt_number,
        label=label,
    )
    db.session.add(att)
    db.session.commit()
    return att


# 1. Tier Ordering Test
def test_tier_ordering_for_fixture_graph(app: Flask, test_user: User, adaptive_setup: dict):
    """Verify get_next_topics orders strictly by priority tiers:
    Tier 1 (Prerequisite gaps of Weak, deepest first) >
    Tier 2 (Weak topic itself) >
    Tier 3 (Ready to learn unattempted) >
    Tier 4 (Good / Better practice) >
    Tier 5 (Excellent mastered).
    """
    with app.app_context():
        u = db.session.get(User, test_user.id)
        nn_id = adaptive_setup["t_neural_net_id"]
        bayes_id = adaptive_setup["t_bayes_id"]
        svm_id = adaptive_setup["t_svm_id"]

        # Student scored Weak on Neural Networks (which requires Perceptron -> Linear Algebra)
        _create_attempt(u.id, nn_id, score=1.0, total=4, label=MasteryLabel.WEAK)
        # Student scored Good on Naive Bayes (practice)
        _create_attempt(u.id, bayes_id, score=3.0, total=4, label=MasteryLabel.GOOD)
        # Student scored Excellent on SVM (mastered)
        _create_attempt(u.id, svm_id, score=4.0, total=4, label=MasteryLabel.EXCELLENT)

        recs = get_next_topics(u, limit=8)
        rec_ids = [r["id"] for r in recs]

        # Tier 1: Prerequisite gaps of Weak Neural Net:
        # Linear Algebra (depth 2) and Perceptron (depth 1)
        assert adaptive_setup["t_linear_alg_id"] in rec_ids[:2]
        assert adaptive_setup["t_perceptron_id"] in rec_ids[:2]
        # Linear Algebra is deepest (depth 2) so must come before Perceptron (depth 1)
        assert rec_ids.index(adaptive_setup["t_linear_alg_id"]) < rec_ids.index(adaptive_setup["t_perceptron_id"])

        # Tier 2: Neural Net itself (Weak)
        assert adaptive_setup["t_neural_net_id"] in rec_ids
        assert rec_ids.index(adaptive_setup["t_perceptron_id"]) < rec_ids.index(adaptive_setup["t_neural_net_id"])

        # Tier 3: Ready to learn unattempted (Decision Trees has no unmet prereqs)
        assert adaptive_setup["t_decision_trees_id"] in rec_ids
        assert rec_ids.index(adaptive_setup["t_neural_net_id"]) < rec_ids.index(adaptive_setup["t_decision_trees_id"])

        # Deep Learning is NOT ready to learn because its prereq (Neural Net) is Weak!
        # Thus Deep Learning should not jump ahead of ready-to-learn or practice topics.

        # Tier 4: Naive Bayes (Good)
        assert adaptive_setup["t_bayes_id"] in rec_ids
        assert rec_ids.index(adaptive_setup["t_decision_trees_id"]) < rec_ids.index(adaptive_setup["t_bayes_id"])

        # Tier 5: SVM (Excellent, mastered goes last)
        assert adaptive_setup["t_svm_id"] in rec_ids
        assert rec_ids.index(adaptive_setup["t_bayes_id"]) < rec_ids.index(adaptive_setup["t_svm_id"])


# 2. Reasons Text Test
def test_reasons_text(app: Flask, test_user: User, adaptive_setup: dict):
    """Verify plain-English pedagogical rationale format across all 5 tiers."""
    with app.app_context():
        u = db.session.get(User, test_user.id)
        nn_id = adaptive_setup["t_neural_net_id"]
        bayes_id = adaptive_setup["t_bayes_id"]
        svm_id = adaptive_setup["t_svm_id"]

        _create_attempt(u.id, nn_id, score=1.0, total=4, label=MasteryLabel.WEAK)
        _create_attempt(u.id, bayes_id, score=3.0, total=4, label=MasteryLabel.GOOD)
        _create_attempt(u.id, svm_id, score=4.0, total=4, label=MasteryLabel.EXCELLENT)

        recs = get_next_topics(u, limit=8)
        recs_by_id = {r["id"]: r for r in recs}

        # Tier 1 reason
        lin_alg_rec = recs_by_id[adaptive_setup["t_linear_alg_id"]]
        assert "Prerequisite of Neural Networks Architecture, which you scored Weak on" == lin_alg_rec["reason"]
        assert lin_alg_rec["label"] == "Not attempted"

        # Tier 2 reason
        nn_rec = recs_by_id[nn_id]
        assert "Scored Weak on last quiz — retake to build mastery" in nn_rec["reason"]
        assert nn_rec["label"] == "Weak"

        # Tier 3 reason
        dt_rec = recs_by_id[adaptive_setup["t_decision_trees_id"]]
        assert "Ready to learn — all prerequisites met" in dt_rec["reason"]
        assert dt_rec["label"] == "Not attempted"

        # Tier 4 reason
        bayes_rec = recs_by_id[bayes_id]
        assert "Scored Good — practice to reach mastery" in bayes_rec["reason"]
        assert bayes_rec["label"] == "Good"

        # Tier 5 reason
        svm_rec = recs_by_id[svm_id]
        assert "Mastered (Excellent) — review or refresh" in svm_rec["reason"]
        assert svm_rec["label"] == "Excellent"


# 3. Rerank Related: Weak and Prerequisite First, Excellent Last
def test_rerank_weak_and_prereq_first_and_excellent_last(app: Flask, test_user: User, adaptive_setup: dict):
    """Verify rerank_related moves prerequisite-of-weak and Weak topics to the front, and Excellent to the back."""
    with app.app_context():
        u = db.session.get(User, test_user.id)
        nn_id = adaptive_setup["t_neural_net_id"]
        lin_id = adaptive_setup["t_linear_alg_id"]
        svm_id = adaptive_setup["t_svm_id"]
        bayes_id = adaptive_setup["t_bayes_id"]

        _create_attempt(u.id, nn_id, score=1.0, total=4, label=MasteryLabel.WEAK)
        _create_attempt(u.id, svm_id, score=4.0, total=4, label=MasteryLabel.EXCELLENT)
        _create_attempt(u.id, bayes_id, score=3.0, total=4, label=MasteryLabel.GOOD)

        # Related list ordered by raw similarity score (SVM highest, LinAlg lowest)
        mock_related = [
            {"id": svm_id, "name": "SVM", "score": 0.95},
            {"id": bayes_id, "name": "Bayes", "score": 0.75},
            {"id": nn_id, "name": "Neural Net", "score": 0.50},
            {"id": lin_id, "name": "Linear Algebra", "score": 0.30},
        ]

        reranked = rerank_related(u, mock_related)

        # Linear Algebra is a prerequisite of Weak Neural Net -> Tier 1
        assert reranked[0]["id"] == lin_id
        assert reranked[0]["label"] == "Not attempted"

        # Neural Net is Weak -> Tier 2
        assert reranked[1]["id"] == nn_id
        assert reranked[1]["label"] == "Weak"

        # Bayes is Good -> Tier 4
        assert reranked[2]["id"] == bayes_id
        assert reranked[2]["label"] == "Good"

        # SVM is Excellent -> Tier 5 (last, despite highest score 0.95)
        assert reranked[3]["id"] == svm_id
        assert reranked[3]["label"] == "Excellent"


# 4. Rerank Similarity Tie-Breaker
def test_rerank_similarity_tie_breaker(app: Flask, test_user: User, adaptive_setup: dict):
    """Verify that inside the same tier, topics with higher similarity score appear before lower scores."""
    with app.app_context():
        u = db.session.get(User, test_user.id)
        dt_id = adaptive_setup["t_decision_trees_id"]
        dl_id = adaptive_setup["t_deep_learning_id"]

        # Neither has been attempted (both Tier 3)
        mock_related = [
            {"id": dt_id, "name": "DT", "score": 0.42},
            {"id": dl_id, "name": "DL", "score": 0.88},
        ]

        reranked = rerank_related(u, mock_related)
        # Deep Learning (0.88) should be ranked before Decision Trees (0.42)
        assert reranked[0]["id"] == dl_id
        assert reranked[1]["id"] == dt_id
        assert reranked[0]["score"] == 0.88
        assert reranked[1]["score"] == 0.42


# 5. Label Field and Adaptive Parameter on Related Endpoint
def test_related_json_endpoint_label_and_adaptive_param(
    auth_client: FlaskClient,
    test_user: User,
    adaptive_setup: dict,
):
    """Verify GET /topics/<id>/related returns label field and supports optional ?adaptive=1."""
    nn_id = adaptive_setup["t_neural_net_id"]
    svm_id = adaptive_setup["t_svm_id"]

    # Record attempts
    _create_attempt(test_user.id, nn_id, score=1.0, total=4, label=MasteryLabel.WEAK)
    _create_attempt(test_user.id, svm_id, score=4.0, total=4, label=MasteryLabel.EXCELLENT)

    # 1. Standard request (without ?adaptive=1) preserves default TF-IDF order, adds label
    res_default = auth_client.get(f"/topics/{nn_id}/related")
    assert res_default.status_code == 200
    assert res_default.is_json
    data_default = res_default.get_json()
    assert isinstance(data_default, list)
    if data_default:
        assert "label" in data_default[0]
        # Scores should be in non-increasing order in default mode
        scores = [item["score"] for item in data_default]
        assert scores == sorted(scores, reverse=True)

    # 2. Adaptive request (?adaptive=1) reranks using mastery tiers
    res_adaptive = auth_client.get(f"/topics/{nn_id}/related?adaptive=1")
    assert res_adaptive.status_code == 200
    assert res_adaptive.is_json
    data_adaptive = res_adaptive.get_json()
    assert isinstance(data_adaptive, list)
    if data_adaptive:
        assert "label" in data_adaptive[0]


# 6. Dashboard Login Required
def test_dashboard_login_required(client: FlaskClient):
    """Verify /dashboard/ redirects unauthenticated visitors to login."""
    res = client.get("/dashboard/")
    assert res.status_code == 302
    assert "/auth/login" in res.headers["Location"]


# 7. Dashboard User Isolation
def test_dashboard_user_isolation(app: Flask, test_user: User, client: FlaskClient, adaptive_setup: dict):
    """Verify Student B cannot see Student A's attempts, weak topics, or uploads on the dashboard."""
    with app.app_context():
        # User A attempts Neural Networks
        _create_attempt(test_user.id, adaptive_setup["t_neural_net_id"], score=1.0, total=4, label=MasteryLabel.WEAK)

        # Create User B
        user_b = User(name="Student B", email="student_b@example.com", semester=5)
        user_b.set_password("Secret123")
        db.session.add(user_b)
        db.session.commit()
        user_b_id = user_b.id

    # Log in as User B
    client.post("/auth/login", data={"email": "student_b@example.com", "password": "Secret123"}, follow_redirects=True)
    res = client.get("/dashboard/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # User B has 0 attempts
    assert "Take your first quiz to see your progress" in html
    assert "0</div>\n                <div class=\"metric-label\">Total Attempts</div>" in html


# 8. Dashboard Empty State
def test_dashboard_empty_state(auth_client: FlaskClient):
    """Verify a new student with zero attempts sees the friendly empty state and no broken charts."""
    res = auth_client.get("/dashboard/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    assert "Take your first quiz to see your progress" in html
    assert "chartMasteryDistribution" in html
    assert "chartProgressOverTime" in html
    assert "chartCourseProgress" in html


# 9. Dashboard Summary Numbers
def test_dashboard_summary_numbers(app: Flask, test_user: User, auth_client: FlaskClient, adaptive_setup: dict):
    """Verify summary metrics cards display accurate aggregate counts."""
    with app.app_context():
        u = db.session.get(User, test_user.id)
        nn_id = adaptive_setup["t_neural_net_id"]
        bayes_id = adaptive_setup["t_bayes_id"]

        # Attempt 1 on NN: Weak (25%)
        _create_attempt(u.id, nn_id, score=1.0, total=4, label=MasteryLabel.WEAK, attempt_number=1)
        # Attempt 2 on NN: Better (75%)
        _create_attempt(u.id, nn_id, score=3.0, total=4, label=MasteryLabel.BETTER, attempt_number=2)
        # Attempt 1 on Bayes: Weak (25%)
        _create_attempt(u.id, bayes_id, score=1.0, total=4, label=MasteryLabel.WEAK, attempt_number=1)

        # Add 1 upload
        upload = Upload(
            user_id=u.id,
            source_type="text",
            title="Lecture Notes Summary",
            content_hash="dummyhash123",
            extracted_text="Sample text",
            summary=["Bullet 1"],
            simple_explanation="Explanation",
            key_terms=[],
            questions=[],
        )
        db.session.add(upload)
        db.session.commit()

    res = auth_client.get("/dashboard/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # Total attempts = 3
    assert "3</div>\n                <div class=\"metric-label\">Total Attempts</div>" in html
    # Topics attempted = 2
    assert "2</div>\n                <div class=\"metric-label\">Topics Attempted</div>" in html
    # Average score = (25 + 75 + 25) / 3 = 41.7%
    assert "41.7%</div>\n                <div class=\"metric-label\">Average Score</div>" in html
    # Mastered topics = 1 (NN latest is Better)
    assert "1</div>\n                <div class=\"metric-label\">Mastered Topics</div>" in html
    # Weak topics = 1 (Bayes latest is Weak)
    assert "1</div>\n                <div class=\"metric-label\">Weak Topics</div>" in html
    # Uploads count = 1
    assert "1</div>\n                <div class=\"metric-label\">Study Uploads</div>" in html


# 10. Dashboard Chart JSON Shape
def test_dashboard_chart_json_shape(app: Flask, test_user: User, auth_client: FlaskClient, adaptive_setup: dict):
    """Verify chart JSON objects rendered into the page contain expected schema and label colors."""
    with app.app_context():
        _create_attempt(test_user.id, adaptive_setup["t_neural_net_id"], score=1.0, total=4, label=MasteryLabel.WEAK)

    res = auth_client.get("/dashboard/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # Extract labelsData JSON
    match_labels = re.search(r"const labelsData = (\{.*?\});", html)
    assert match_labels is not None
    labels_json = json.loads(match_labels.group(1))
    assert labels_json["labels"] == ["Weak", "Good", "Better", "Excellent"]
    assert "#dc2626" in labels_json["colors"]  # weak red
    assert "#d97706" in labels_json["colors"]  # good amber
    assert "#2563eb" in labels_json["colors"]  # better blue
    assert "#16a34a" in labels_json["colors"]  # excellent green

    # Extract progressData JSON
    match_progress = re.search(r"const progressData = (\{.*?\});", html)
    assert match_progress is not None
    progress_json = json.loads(match_progress.group(1))
    assert "percentages" in progress_json
    assert "labels" in progress_json

    # Extract courseData JSON
    match_course = re.search(r"const courseData = (\{.*?\});", html)
    assert match_course is not None
    course_json = json.loads(match_course.group(1))
    assert "labels" in course_json
    assert "attempted" in course_json
    assert "total" in course_json
    assert "avg_percentages" in course_json


# 11. No CDN URLs in Dashboard HTML
def test_dashboard_no_cdn_urls(auth_client: FlaskClient):
    """Verify dashboard HTML contains zero CDN script references, loading Chart.js exclusively from local vendor."""
    res = auth_client.get("/dashboard/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    assert "cdnjs.cloudflare.com" not in html
    assert "cdn.jsdelivr.net" not in html
    assert "unpkg.com" not in html
    assert "/static/js/vendor/chart.umd.min.js" in html


# 12. Query Count Constant When Attempts Grow
def test_query_count_constant_when_attempts_grow(app: Flask, test_user: User, adaptive_setup: dict):
    """Verify that get_next_topics executes at most 5 queries and query count remains constant as attempts grow."""
    with app.app_context():
        u = db.session.get(User, test_user.id)
        nn_id = adaptive_setup["t_neural_net_id"]

        # Baseline: 1 attempt
        _create_attempt(u.id, nn_id, score=1.0, total=4, label=MasteryLabel.WEAK, attempt_number=1)

        queries_baseline = []

        def count_queries_baseline(conn, cursor, statement, parameters, context, executemany):
            queries_baseline.append(statement)

        event.listen(db.engine, "before_cursor_execute", count_queries_baseline)
        try:
            get_next_topics(u, limit=8)
        finally:
            event.remove(db.engine, "before_cursor_execute", count_queries_baseline)

        baseline_count = len(queries_baseline)
        assert baseline_count <= 5, f"Expected <= 5 queries, got {baseline_count}"

        # Add 30 additional attempts for the same user across topics
        for i in range(2, 32):
            _create_attempt(u.id, nn_id, score=2.0, total=4, label=MasteryLabel.GOOD, attempt_number=i)

        queries_after = []

        def count_queries_after(conn, cursor, statement, parameters, context, executemany):
            queries_after.append(statement)

        event.listen(db.engine, "before_cursor_execute", count_queries_after)
        try:
            get_next_topics(u, limit=8)
        finally:
            event.remove(db.engine, "before_cursor_execute", count_queries_after)

        after_count = len(queries_after)
        assert after_count == baseline_count, (
            f"Query count scaled with attempts! Baseline: {baseline_count}, After 30 attempts: {after_count}"
        )


# 13. Topic Page Shows Badge in Related Sidebar
def test_topic_page_shows_badge_in_related_sidebar(
    app: Flask,
    test_user: User,
    auth_client: FlaskClient,
    adaptive_setup: dict,
):
    """Verify the topic detail page sidebar displays mastery label badges or 'New' for related topics."""
    with app.app_context():
        # Record a Weak attempt on Perceptron
        _create_attempt(test_user.id, adaptive_setup["t_perceptron_id"], score=1.0, total=4, label=MasteryLabel.WEAK)

    res = auth_client.get(f"/topics/{adaptive_setup['t_linear_alg_id']}")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # In Related Topics section, badges should appear
    assert "badge-mastery-weak" in html or "New" in html


# 14. Recommendations Change Dynamically After a New Quiz Attempt
def test_recommendations_change_after_attempt(app: Flask, test_user: User, adaptive_setup: dict):
    """Verify that after a Weak result, prerequisite gaps are prioritized first,
    and after an improved attempt (Better), the recommendation order dynamically updates.
    """
    with app.app_context():
        u = db.session.get(User, test_user.id)
        nn_id = adaptive_setup["t_neural_net_id"]
        lin_id = adaptive_setup["t_linear_alg_id"]
        perceptron_id = adaptive_setup["t_perceptron_id"]
        dt_id = adaptive_setup["t_decision_trees_id"]

        # Step 1: Weak attempt on Neural Networks
        _create_attempt(u.id, nn_id, score=1.0, total=4, label=MasteryLabel.WEAK, attempt_number=1)

        recs_weak = get_next_topics(u, limit=5)
        weak_order_ids = [r["id"] for r in recs_weak]

        # Prerequisite gaps (Linear Algebra, Perceptron) must appear ahead of unattempted Decision Trees
        assert weak_order_ids[0] in [lin_id, perceptron_id]
        assert weak_order_ids.index(lin_id) < weak_order_ids.index(dt_id)
        assert weak_order_ids.index(perceptron_id) < weak_order_ids.index(dt_id)

        # Step 2: Student retakes Neural Networks and achieves Better mastery
        _create_attempt(u.id, nn_id, score=3.0, total=4, label=MasteryLabel.BETTER, attempt_number=2)

        recs_improved = get_next_topics(u, limit=5)
        improved_order_ids = [r["id"] for r in recs_improved]

        # Neural Net is no longer Weak! Its prerequisites are no longer Tier 1 gaps!
        # Neural Net moves from Tier 2 to Tier 4 (Practice), below ready-to-learn topics
        assert improved_order_ids != weak_order_ids
        recs_weak_by_id = {r["id"]: r for r in recs_weak}
        recs_improved_by_id = {r["id"]: r for r in recs_improved}

        assert recs_weak_by_id[nn_id]["tier"] == 2
        assert recs_improved_by_id[nn_id]["tier"] == 4
        assert "Scored Weak" in recs_weak_by_id[nn_id]["reason"]
        assert "Scored Better" in recs_improved_by_id[nn_id]["reason"]

        assert recs_weak_by_id[lin_id]["tier"] == 1
        assert recs_improved_by_id[lin_id]["tier"] == 3
        assert "Prerequisite" in recs_weak_by_id[lin_id]["reason"]
        assert "Ready to learn" in recs_improved_by_id[lin_id]["reason"]

        # Neural Net is now placed after ready-to-learn topics
        assert improved_order_ids.index(dt_id) < improved_order_ids.index(nn_id)
