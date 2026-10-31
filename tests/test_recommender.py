"""Unit and integration tests for the TF-IDF content-based topic recommender."""

from __future__ import annotations

import pytest
from flask import Flask
from flask.testing import FlaskClient
from app.extensions import db
from app.models.course import Course
from app.models.topic import Topic, ContentSource
from app.services.recommendation_service import (
    reset_recommender,
    get_recommender,
    get_recommendations,
    get_related_topics,
)
from ml.recommender import TopicRecommender


@pytest.fixture(autouse=True)
def clean_recommender_state():
    """Ensure recommender singleton state is reset before and after every test."""
    reset_recommender()
    yield
    reset_recommender()


@pytest.fixture
def recommender_sample_topics() -> list[dict]:
    """Provide a small in-memory fixture dataset of ML and OS topics."""
    return [
        {
            "id": 1,
            "name": "Supervised Learning and Linear Regression",
            "subject": "Machine Learning",
            "description": "Foundations of supervised machine learning and continuous linear regression models.",
            "tags": ["machine-learning", "supervised", "regression", "cost-function"],
            "content": (
                "Supervised learning trains predictive algorithms on labeled input datasets. "
                "Linear regression minimizes mean squared error using gradient descent optimization."
            ),
        },
        {
            "id": 2,
            "name": "Logistic Regression and Classification",
            "subject": "Machine Learning",
            "description": "Binary and multiclass classification using logistic sigmoid hypotheses and cross-entropy loss.",
            "tags": ["machine-learning", "classification", "regression", "logistic"],
            "content": (
                "Logistic regression models the probability of discrete class outcomes using the sigmoid activation function. "
                "It serves as a fundamental supervised learning benchmark for binary classification problems."
            ),
        },
        {
            "id": 3,
            "name": "Support Vector Machines",
            "subject": "Machine Learning",
            "description": "Maximum margin hyperplane classifiers and kernel trick transformations.",
            "tags": ["machine-learning", "svm", "classification", "kernels"],
            "content": (
                "Support vector machines maximize the geometric margin between decision boundaries and support vectors. "
                "Kernel functions project non-linearly separable feature spaces into higher dimensional representations."
            ),
        },
        {
            "id": 4,
            "name": "Process Scheduling and CPU Allocation",
            "subject": "Operating Systems",
            "description": "Operating system CPU scheduling algorithms including Round Robin, FCFS, and multi-level feedback queues.",
            "tags": ["operating-systems", "processes", "scheduling", "cpu"],
            "content": (
                "Operating system kernels manage preemptive multitasking through CPU scheduling algorithms. "
                "The dispatcher performs context switching to transfer processor control between ready threads."
            ),
        },
        {
            "id": 5,
            "name": "Virtual Memory and Paging",
            "subject": "Operating Systems",
            "description": "Demand paging, page replacement algorithms (LRU, FIFO), and translation lookaside buffers.",
            "tags": ["operating-systems", "memory", "paging", "virtual-memory"],
            "content": (
                "Virtual memory maps logical process address spaces to physical RAM frames using page tables. "
                "Page faults trigger operating system disk swaps when requested pages are absent from physical memory."
            ),
        },
    ]


@pytest.fixture
def seeded_db_curriculum(app: Flask):
    """Seed test database with courses and topics for recommender endpoint and template verification."""
    with app.app_context():
        ml_course = Course(
            code="CS310",
            title="Machine Learning",
            semester=5,
            domain="Computing Core",
            credit_hours=3,
            contact_hours="3-0",
            is_elective=False,
        )
        os_course = Course(
            code="CS301",
            title="Operating Systems",
            semester=5,
            domain="Computing Core",
            credit_hours=3,
            contact_hours="3-0",
            is_elective=False,
        )
        db.session.add_all([ml_course, os_course])
        db.session.commit()

        t1 = Topic(
            course_id=ml_course.id,
            semester=5,
            subject="Machine Learning",
            name="Supervised Learning Foundations",
            difficulty=2,
            week="1",
            description="Supervised learning overview and regression models.",
            tags=["machine-learning", "regression", "supervised"],
            content="Supervised learning trains predictive algorithms on labeled input datasets with linear regression.",
            content_source=ContentSource.LECTURE,
            content_reviewed=True,
        )
        t2 = Topic(
            course_id=ml_course.id,
            semester=5,
            subject="Machine Learning",
            name="Linear Regression Analysis",
            difficulty=2,
            week="2",
            description="Cost functions and gradient descent for linear regression.",
            tags=["regression", "gradient-descent", "machine-learning"],
            content="Linear regression optimizes cost functions using gradient descent for continuous target predictions.",
            content_source=ContentSource.LECTURE,
            content_reviewed=True,
        )
        t3 = Topic(
            course_id=ml_course.id,
            semester=5,
            subject="Machine Learning",
            name="Logistic Classification Models",
            difficulty=3,
            week="3",
            description="Classification with logistic regression and decision boundaries.",
            tags=["classification", "logistic", "machine-learning"],
            content="Logistic regression estimates classification class probabilities using sigmoid activation.",
            content_source=ContentSource.LECTURE,
            content_reviewed=True,
        )
        t4 = Topic(
            course_id=os_course.id,
            semester=5,
            subject="Operating Systems",
            name="Process Management and Scheduling",
            difficulty=3,
            week="1",
            description="Process lifecycle, threads, and CPU dispatching.",
            tags=["operating-systems", "processes", "scheduling"],
            content="Operating system kernels manage process lifecycle, CPU scheduling, and context switching.",
            content_source=ContentSource.LECTURE,
            content_reviewed=True,
        )
        t5 = Topic(
            course_id=os_course.id,
            semester=5,
            subject="Operating Systems",
            name="Isolated Topic Without Overlap",
            difficulty=1,
            week="10",
            description="Quantum mechanics and astrophysics principles.",
            tags=["physics", "astronomy"],
            content="Spectroscopy analyzes celestial light spectra across telescope focal arrays.",
            content_source=ContentSource.LECTURE,
            content_reviewed=False,
        )

        db.session.add_all([t1, t2, t3, t4, t5])
        db.session.commit()

        return {
            "ml_course_id": ml_course.id,
            "os_course_id": os_course.id,
            "t1_id": t1.id,
            "t2_id": t2.id,
            "t3_id": t3.id,
            "t4_id": t4.id,
            "isolated_id": t5.id,
        }


# ==============================================================================
# Unit Tests for TopicRecommender class
# ==============================================================================

def test_recommender_sensible_ranking(recommender_sample_topics: list[dict]):
    """Verify that similar ML topics rank strictly above unrelated OS topics."""
    recommender = TopicRecommender(same_subject_boost=0.05)
    recommender.fit(recommender_sample_topics)

    # Query for Topic 1: "Supervised Learning and Linear Regression"
    recommendations = recommender.recommend(topic_id=1, k=5)
    assert len(recommendations) > 0

    rec_ids = [topic_id for topic_id, _ in recommendations]
    scores = {topic_id: score for topic_id, score in recommendations}

    # Topic 2 (Logistic Regression) and Topic 3 (SVM) should rank above OS topics (4 and 5)
    assert 2 in rec_ids
    assert 3 in rec_ids

    # Check score ordering: ML topics score higher than OS topics
    if 4 in scores:
        assert scores[2] > scores[4]
        assert scores[3] > scores[4]
    if 5 in scores:
        assert scores[2] > scores[5]
        assert scores[3] > scores[5]

    # Verify descending score sorting
    score_list = [score for _, score in recommendations]
    assert score_list == sorted(score_list, reverse=True)


def test_recommender_excludes_itself(recommender_sample_topics: list[dict]):
    """Verify that a topic is never recommended to itself."""
    recommender = TopicRecommender()
    recommender.fit(recommender_sample_topics)

    for item in recommender_sample_topics:
        recs = recommender.recommend(topic_id=item["id"], k=5)
        rec_ids = [t_id for t_id, _ in recs]
        assert item["id"] not in rec_ids


def test_recommender_k_limit(recommender_sample_topics: list[dict]):
    """Verify that the k parameter strictly bounds the result length."""
    recommender = TopicRecommender()
    recommender.fit(recommender_sample_topics)

    recs_k1 = recommender.recommend(topic_id=1, k=1)
    assert len(recs_k1) == 1

    recs_k2 = recommender.recommend(topic_id=1, k=2)
    assert len(recs_k2) == 2

    recs_k10 = recommender.recommend(topic_id=1, k=10)
    # Total available candidates is at most len(topics) - 1
    assert len(recs_k10) <= 4


def test_recommender_unknown_id(recommender_sample_topics: list[dict]):
    """Verify that unknown topic IDs safely return an empty list without raising."""
    recommender = TopicRecommender()
    recommender.fit(recommender_sample_topics)

    recs = recommender.recommend(topic_id=999999, k=5)
    assert recs == []


def test_recommender_tiny_and_edge_case_datasets():
    """Verify safe handling of empty datasets, single topics, and stop-word documents."""
    recommender = TopicRecommender()

    # Empty dataset
    recommender.fit([])
    assert recommender.recommend(1) == []

    # Single topic dataset
    single_topic = [
        {"id": 10, "name": "Solo Topic", "description": "No peers", "content": "Lone content", "subject": "Math"}
    ]
    recommender.fit(single_topic)
    assert recommender.recommend(10) == []

    # Stop-word-only documents (should not crash TfidfVectorizer with ValueError)
    stopword_topics = [
        {"id": 1, "name": "The and of", "description": "a in", "content": "to is was", "subject": "General"},
        {"id": 2, "name": "For with on", "description": "by at", "content": "from that this", "subject": "General"},
    ]
    recommender.fit(stopword_topics)
    assert recommender.recommend(1) == []


def test_recommender_same_subject_boost():
    """Verify that same-subject topics receive the configured additive boost."""
    topics = [
        {
            "id": 1,
            "name": "Neural Network Optimization",
            "subject": "Deep Learning",
            "description": "Gradient descent and backpropagation algorithms.",
            "tags": ["neural-networks", "optimization"],
            "content": "Gradient descent optimization updates network weights.",
        },
        {
            "id": 2,
            "name": "Convolutional Neural Networks",
            "subject": "Deep Learning",  # Same subject
            "description": "Deep vision models with gradient descent optimization.",
            "tags": ["cnn", "optimization"],
            "content": "Gradient descent trains convolution filter weights.",
        },
        {
            "id": 3,
            "name": "Numerical Gradient Optimization",
            "subject": "Calculus",  # Different subject with similar vocabulary
            "description": "Multivariate gradient descent optimization for convex functions.",
            "tags": ["math", "optimization"],
            "content": "Gradient descent iteratively converges toward local minima.",
        },
    ]

    recommender_no_boost = TopicRecommender(same_subject_boost=0.0)
    recommender_no_boost.fit(topics)
    scores_no_boost = dict(recommender_no_boost.recommend(1, k=5))

    recommender_with_boost = TopicRecommender(same_subject_boost=0.08)
    recommender_with_boost.fit(topics)
    scores_with_boost = dict(recommender_with_boost.recommend(1, k=5))

    # Topic 2 (same subject) should receive +0.08 boost
    assert pytest.approx(scores_with_boost[2] - scores_no_boost[2], 0.001) == 0.08
    # Topic 3 (different subject) score remains unboosted
    assert pytest.approx(scores_with_boost[3], 0.001) == scores_no_boost[3]


# ==============================================================================
# Service Integration Tests
# ==============================================================================

def test_service_lazy_build_and_invalidation(app: Flask, seeded_db_curriculum: dict):
    """Verify that recommendation_service lazily fits and caches, rebuilding on changes."""
    with app.app_context():
        # First call builds lazily
        recommender1 = get_recommender()
        assert recommender1 is not None

        # Second call returns cached singleton
        recommender2 = get_recommender()
        assert recommender1 is recommender2

        # Add a new topic to mutate database state key
        new_topic = Topic(
            course_id=seeded_db_curriculum["ml_course_id"],
            semester=5,
            subject="Machine Learning",
            name="Deep Reinforcement Learning",
            difficulty=4,
            week="12",
            description="Q-learning and policy gradients.",
            tags=["rl", "q-learning"],
            content="Reinforcement learning agents optimize expected cumulative reward.",
            content_source=ContentSource.LECTURE,
            content_reviewed=True,
        )
        db.session.add(new_topic)
        db.session.commit()

        # Service should automatically detect state change and rebuild
        recommender3 = get_recommender()
        assert recommender3 is not recommender1
        recs = get_recommendations(new_topic.id, k=3)
        assert isinstance(recs, list)


def test_service_get_related_topics_format(app: Flask, seeded_db_curriculum: dict):
    """Verify get_related_topics returns required dictionary format and properties."""
    with app.app_context():
        t1_id = seeded_db_curriculum["t1_id"]
        results = get_related_topics(topic_id=t1_id, k=5)
        assert len(results) > 0

        for item in results:
            assert "id" in item
            assert "name" in item
            assert "course" in item
            assert "week" in item
            assert "difficulty" in item
            assert "score" in item
            assert isinstance(item["id"], int)
            assert isinstance(item["name"], str)
            assert isinstance(item["course"], str)
            assert isinstance(item["difficulty"], int)
            assert isinstance(item["score"], float)
            assert item["id"] != t1_id


# ==============================================================================
# Blueprint & Endpoint Tests
# ==============================================================================

def test_endpoint_login_required(client: FlaskClient, seeded_db_curriculum: dict):
    """Verify GET /topics/<id>/related redirects unauthenticated requests to login."""
    t1_id = seeded_db_curriculum["t1_id"]
    response = client.get(f"/topics/{t1_id}/related")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_endpoint_json_success(auth_client: FlaskClient, seeded_db_curriculum: dict):
    """Verify GET /topics/<id>/related returns 200 JSON list with expected structure."""
    t1_id = seeded_db_curriculum["t1_id"]
    response = auth_client.get(f"/topics/{t1_id}/related")
    assert response.status_code == 200
    assert response.is_json

    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert len(data) <= 5

    first = data[0]
    expected_keys = {"id", "name", "course", "week", "difficulty", "score"}
    assert expected_keys.issubset(first.keys())
    assert first["id"] != t1_id
    assert first["course"] in ["Machine Learning", "Operating Systems"]


def test_endpoint_unknown_id(auth_client: FlaskClient, seeded_db_curriculum: dict):
    """Verify GET /topics/<id>/related returns 404 for non-existent topic ID."""
    response = auth_client.get("/topics/999999/related")
    assert response.status_code == 404


def test_topic_page_shows_related_section(auth_client: FlaskClient, seeded_db_curriculum: dict):
    """Verify /topics/<id> renders the Related Topics section with cards and links."""
    t1_id = seeded_db_curriculum["t1_id"]
    response = auth_client.get(f"/topics/{t1_id}")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert "Related Topics" in html
    assert "related-topics-section" in html
    assert "related-topic-card" in html
    # Check that similar ML topic title appears in related section
    assert "Linear Regression Analysis" in html or "Logistic Classification Models" in html


def test_topic_page_shows_empty_message_when_no_recommendations(auth_client: FlaskClient, seeded_db_curriculum: dict):
    """Verify /topics/<id> displays friendly empty message when no related topics exist."""
    isolated_id = seeded_db_curriculum["isolated_id"]
    response = auth_client.get(f"/topics/{isolated_id}")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert "Related Topics" in html
    assert "No related topics found" in html
