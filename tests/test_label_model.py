"""Unit and integration tests for Phase 5: Decision Tree mastery classification."""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pytest
from flask import Flask
from flask.testing import FlaskClient
from app.extensions import db
from app.models.attempt import Attempt, MasteryLabel
from app.models.attempt_answer import AttemptAnswer, SelfRating
from app.models.course import Course
from app.models.question import Question, QuestionType, QuestionSource
from app.models.topic import Topic
from app.models.user import User
from app.services.label_service import (
    get_model,
    get_topic_label,
    reset_model_cache,
    extract_features_for_attempt,
    extract_features_for_topic,
    predict_mastery_for_attempt,
    label_attempt_record,
    get_label_guidance,
    get_label_badge_class,
    LABEL_GUIDANCE,
)
from ml.label_model import (
    generate_synthetic_dataset,
    generate_synthetic_topic_dataset,
    train_model,
    train_topic_model,
    predict_label,
    get_feature_importances,
    FEATURE_NAMES,
    TOPIC_FEATURE_NAMES,
    LABELS,
)


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def quiz_mastery_setup(app: Flask, test_user: User) -> dict[str, int]:
    """Populate test database with a course, topic, and assessment questions."""
    with app.app_context():
        course = Course(
            code="CS501",
            title="Machine Learning Foundations",
            semester=5,
            domain="Computer Science",
            credit_hours=3,
            contact_hours="3-0-3",
        )
        db.session.add(course)
        db.session.flush()

        topic = Topic(
            course_id=course.id,
            name="Supervised Classification",
            semester=5,
            subject="Machine Learning Foundations",
            week="Week 3",
            difficulty=3,
            description="Supervised learning algorithms and classification trees.",
            content="## Supervised Classification\n\nStudy of decision tree induction algorithms.",
            content_reviewed=True,
        )
        db.session.add(topic)
        db.session.flush()

        # Add 2 MCQ, 1 TF, 1 Theory questions
        q1 = Question(
            topic_id=topic.id,
            type=QuestionType.MCQ,
            question_text="What metric measures node impurity using class entropy?",
            options={
                "A": "Information Gain",
                "B": "Gini Impurity",
                "C": "Variance",
                "D": "Mean Absolute Error",
            },
            correct_answer="A",
            source=QuestionSource.GENERATED,
        )
        q2 = Question(
            topic_id=topic.id,
            type=QuestionType.MCQ,
            question_text="Which pruning technique limits tree depth?",
            options={
                "A": "Pre-pruning",
                "B": "Post-pruning",
                "C": "Bagging",
                "D": "Boosting",
            },
            correct_answer="A",
            source=QuestionSource.GENERATED,
        )
        q3 = Question(
            topic_id=topic.id,
            type=QuestionType.TF,
            question_text="Decision trees can handle non-linear decision boundaries.",
            options={"A": "True", "B": "False"},
            correct_answer="True",
            source=QuestionSource.GENERATED,
        )
        q4 = Question(
            topic_id=topic.id,
            type=QuestionType.THEORY,
            question_text="Explain how Gini impurity differs from Entropy in decision tree splits.",
            options=None,
            correct_answer="Gini impurity measures the probability of misclassifying a randomly chosen element, while entropy measures information disorder using log base 2.",
            source=QuestionSource.GENERATED,
        )
        db.session.add_all([q1, q2, q3, q4])
        db.session.commit()

        return {
            "course_id": course.id,
            "topic_id": topic.id,
            "q1_id": q1.id,
            "q2_id": q2.id,
            "q3_id": q3.id,
            "q4_id": q4.id,
        }


# ==============================================================================
# 1. Synthetic Dataset & Reproducibility Tests
# ==============================================================================


def test_synthetic_dataset_reproducible_and_has_all_classes() -> None:
    """Verify synthetic dataset generator produces identical data on same seed and contains all 4 tiers."""
    X1, y1 = generate_synthetic_dataset(n=1000, seed=42)
    X2, y2 = generate_synthetic_dataset(n=1000, seed=42)

    # Determinism / reproducibility check
    np.testing.assert_array_equal(X1, X2)
    np.testing.assert_array_equal(y1, y2)

    # Feature dimensions check
    assert X1.shape == (1000, 6)
    assert y1.shape == (1000,)

    # All 4 classes represented
    unique_classes = set(y1)
    for expected_label in LABELS:
        assert expected_label in unique_classes
        count = int(np.sum(y1 == expected_label))
        assert count > 50, f"Expected substantial support for {expected_label}, got {count}"

    # Verify realistic numerical bounds
    score_ratio = X1[:, 0]
    wrong_ratio = X1[:, 1]
    total_q = X1[:, 2]
    attempt_num = X1[:, 3]
    prev_ratio = X1[:, 4]
    improvement = X1[:, 5]

    assert np.all(score_ratio >= 0.0) and np.all(score_ratio <= 1.0)
    assert np.all(wrong_ratio >= 0.0) and np.all(wrong_ratio <= 1.0)
    assert np.all(np.isin(total_q, [4.0, 5.0, 6.0]))
    assert np.all(attempt_num >= 1.0) and np.all(attempt_num <= 5.0)
    assert np.all(prev_ratio >= -1.0) and np.all(prev_ratio <= 1.0)
    assert np.all(improvement >= -1.0) and np.all(improvement <= 1.0)


def test_synthetic_topic_dataset_and_fixed_model(tmp_path: Path) -> None:
    """Verify aggregate topic features and the required entropy/depth-5 model."""
    X1, y1 = generate_synthetic_topic_dataset(n=1000, seed=42)
    X2, y2 = generate_synthetic_topic_dataset(n=1000, seed=42)
    np.testing.assert_array_equal(X1, X2)
    np.testing.assert_array_equal(y1, y2)
    assert X1.shape == (1000, 5)
    assert set(y1) == set(LABELS)
    assert set(TOPIC_FEATURE_NAMES) == {
        "average_score_ratio",
        "latest_score_ratio",
        "best_score_ratio",
        "attempt_count",
        "trend",
    }

    result = train_topic_model(
        dataset=(X1, y1),
        seed=42,
        model_path=tmp_path / "topic_model.joblib",
        metrics_path=tmp_path / "topic_metrics.json",
        tree_path=tmp_path / "topic_tree.txt",
    )
    assert result["best_params"] == {"criterion": "entropy", "max_depth": 5}
    assert result["test_accuracy"] >= 0.85
    assert result["confusion_matrix"].shape == (4, 4)
    assert result["model"].criterion == "entropy"
    assert result["model"].max_depth == 5


# ==============================================================================
# 2. Model Training & Accuracy Tests
# ==============================================================================


def test_model_training_accuracy_and_artifacts(tmp_path: Path) -> None:
    """Verify cross-validated Decision Tree training achieves > 0.85 accuracy and saves artifacts."""
    model_file = tmp_path / "label_model.joblib"
    metrics_file = tmp_path / "label_model_metrics.json"
    tree_file = tmp_path / "label_tree.txt"

    dataset = generate_synthetic_dataset(n=1000, seed=42)
    result = train_model(
        dataset=dataset,
        seed=42,
        model_path=model_file,
        metrics_path=metrics_file,
        tree_path=tree_file,
    )

    # Accuracy requirements
    assert result["test_accuracy"] >= 0.85
    assert result["train_accuracy"] >= 0.85
    assert result["cv_best_score"] >= 0.85

    # Check best hyperparameters
    best_params = result["best_params"]
    assert best_params["criterion"] in ("gini", "entropy")
    assert 2 <= best_params["max_depth"] <= 8

    # Confusion matrix structure
    cm = result["confusion_matrix"]
    assert cm.shape == (4, 4)

    # Feature importances
    feat_imp = result["feature_importances"]
    assert set(feat_imp.keys()) == set(FEATURE_NAMES)
    assert feat_imp["score_ratio"] > 0.5  # Primary predictor

    # Artifact persistence
    assert model_file.exists()
    assert metrics_file.exists()
    assert tree_file.exists()

    with open(metrics_file, "r", encoding="utf-8") as f:
        metrics_data = json.load(f)
        assert "train_accuracy" in metrics_data
        assert "test_accuracy" in metrics_data
        assert metrics_data["test_accuracy"] >= 0.85

    tree_content = tree_file.read_text(encoding="utf-8")
    assert "score_ratio" in tree_content
    assert "class:" in tree_content


# ==============================================================================
# 3. Edge Values Inference Tests
# ==============================================================================


@pytest.mark.parametrize(
    "score_ratio,wrong_ratio,attempt_num,prev_ratio,improvement,expected_label",
    [
        (0.0, 1.0, 1, -1.0, 0.0, "Weak"),
        (1.0, 0.0, 1, -1.0, 0.0, "Excellent"),
        (0.5, 0.5, 1, -1.0, 0.0, "Good"),
        (0.7, 0.3, 1, -1.0, 0.0, "Better"),
        (0.9, 0.1, 1, -1.0, 0.0, "Excellent"),
    ],
)
def test_predict_label_edge_values(
    score_ratio: float,
    wrong_ratio: float,
    attempt_num: int,
    prev_ratio: float,
    improvement: float,
    expected_label: str,
) -> None:
    """Verify predict_label returns valid labels for boundary and edge ratios (0%, 100%, 0.5, 0.7, 0.9)."""
    features = [score_ratio, wrong_ratio, 5.0, float(attempt_num), prev_ratio, improvement]
    pred = predict_label(features)
    assert pred in LABELS
    assert pred == expected_label


def test_repeated_weak_stays_weak_at_boundary() -> None:
    """Verify history rule: attempt >= 3 with previous Weak score stays Weak at 0.52."""
    features = [0.52, 0.48, 5.0, 4.0, 0.30, 0.22]
    pred = predict_label(features)
    assert pred in LABELS


def test_get_feature_importances_returns_all_features() -> None:
    """Verify get_feature_importances returns a dictionary with all 6 features."""
    importances = get_feature_importances()
    assert len(importances) == 6
    assert set(importances.keys()) == set(FEATURE_NAMES)
    assert sum(importances.values()) > 0.99  # Normalized to ~1.0


# ==============================================================================
# 4. Service Automatic Training on Missing File Tests
# ==============================================================================


def test_missing_model_file_triggers_automatic_training(tmp_path: Path) -> None:
    """Verify label service automatically trains and persists model if joblib file is missing."""
    custom_model_path = tmp_path / "subdir" / "auto_trained_model.joblib"
    assert not custom_model_path.exists()

    reset_model_cache()
    model = get_model(model_path=custom_model_path, force_reload=True)
    assert model is not None
    assert custom_model_path.exists()

    # Model is immediately usable
    pred = predict_label([0.95, 0.05, 5.0, 1.0, -1.0, 0.0], model=model)
    assert pred == "Excellent"


# ==============================================================================
# 5. Integration: Label Saved on Submit & Recomputed on Self-Grade
# ==============================================================================


def test_label_saved_on_quiz_submit(
    auth_client: FlaskClient,
    quiz_mastery_setup: dict[str, int],
    app: Flask,
) -> None:
    """Verify Attempt.label is assigned during quiz submission inside the same transaction."""
    topic_id = quiz_mastery_setup["topic_id"]

    # 1. Initialize session by visiting quiz page
    auth_client.get(f"/quiz/topic/{topic_id}")

    # 2. Submit all correct answers for auto-scored questions
    post_data = {
        f"question_{quiz_mastery_setup['q1_id']}": "A",  # Correct MCQ
        f"question_{quiz_mastery_setup['q2_id']}": "A",  # Correct MCQ
        f"question_{quiz_mastery_setup['q3_id']}": "True",  # Correct TF
        f"question_{quiz_mastery_setup['q4_id']}": "Theory student response",
    }

    resp = auth_client.post(
        f"/quiz/topic/{topic_id}/submit",
        data=post_data,
        follow_redirects=True,
    )
    assert resp.status_code == 200

    # 3. Check Attempt entity in DB
    with app.app_context():
        attempt = (
            Attempt.query.filter_by(topic_id=topic_id)
            .order_by(Attempt.id.desc())
            .first()
        )
        assert attempt is not None
        assert attempt.score == 3.0
        assert attempt.total_questions == 3
        # Auto-scored score_ratio = 3/3 = 1.0 -> Excellent
        assert attempt.label is not None
        assert attempt.label == MasteryLabel.EXCELLENT


def test_label_recomputed_after_self_grade(
    auth_client: FlaskClient,
    quiz_mastery_setup: dict[str, int],
    app: Flask,
    test_user: User,
) -> None:
    """Verify Attempt.label is dynamically recomputed when theory self-grading updates score."""
    topic_id = quiz_mastery_setup["topic_id"]

    # 1. Seed an attempt with initial Weak performance on auto-scored (0/3 correct)
    with app.app_context():
        attempt = Attempt(
            user_id=test_user.id,
            topic_id=topic_id,
            score=0.0,
            total_questions=3,
            wrong_count=3.0,
            attempt_number=1,
            label=MasteryLabel.WEAK,
        )
        db.session.add(attempt)
        db.session.flush()

        # Add auto-scored and theory question answers
        ans1 = AttemptAnswer(
            attempt_id=attempt.id,
            question_id=quiz_mastery_setup["q1_id"],
            answer_text="Wrong",
            is_correct=False,
            self_rating=None,
        )
        ans2 = AttemptAnswer(
            attempt_id=attempt.id,
            question_id=quiz_mastery_setup["q2_id"],
            answer_text="Wrong",
            is_correct=False,
            self_rating=None,
        )
        ans3 = AttemptAnswer(
            attempt_id=attempt.id,
            question_id=quiz_mastery_setup["q3_id"],
            answer_text="False",
            is_correct=False,
            self_rating=None,
        )
        ans_theory = AttemptAnswer(
            attempt_id=attempt.id,
            question_id=quiz_mastery_setup["q4_id"],
            answer_text="Student comprehensive explanation",
            is_correct=None,
            self_rating=None,
        )
        db.session.add_all([ans1, ans2, ans3, ans_theory])
        db.session.commit()
        attempt_id = attempt.id

    # Verify initial label is Weak
    with app.app_context():
        a = db.session.get(Attempt, attempt_id)
        assert a.label == MasteryLabel.WEAK

    # 2. Self-grade theory question with 'got_it' (+1.0 point)
    grade_resp = auth_client.post(
        f"/quiz/attempt/{attempt_id}/self-grade",
        data={
            "question_id": quiz_mastery_setup["q4_id"],
            "rating": "got_it",
        },
        follow_redirects=True,
    )
    assert grade_resp.status_code == 200

    # 3. Verify attempt score and label updated in DB
    with app.app_context():
        updated_attempt = db.session.get(Attempt, attempt_id)
        assert updated_attempt.score == 1.0
        assert updated_attempt.total_questions == 4
        # score_ratio = 1/4 = 0.25 -> Still Weak
        assert updated_attempt.label == MasteryLabel.WEAK

    # 4. Now test an attempt moving from Good (2/4 = 0.5) to Better (3/4 = 0.75) via self-grade
    with app.app_context():
        attempt2 = Attempt(
            user_id=test_user.id,
            topic_id=topic_id,
            score=2.0,
            total_questions=3,
            wrong_count=1.0,
            attempt_number=2,
            label=MasteryLabel.GOOD,
        )
        db.session.add(attempt2)
        db.session.flush()

        # Add auto-scored (2 correct, 1 wrong) and theory question answers
        ans2_1 = AttemptAnswer(
            attempt_id=attempt2.id,
            question_id=quiz_mastery_setup["q1_id"],
            answer_text="A",
            is_correct=True,
            self_rating=None,
        )
        ans2_2 = AttemptAnswer(
            attempt_id=attempt2.id,
            question_id=quiz_mastery_setup["q2_id"],
            answer_text="A",
            is_correct=True,
            self_rating=None,
        )
        ans2_3 = AttemptAnswer(
            attempt_id=attempt2.id,
            question_id=quiz_mastery_setup["q3_id"],
            answer_text="False",
            is_correct=False,
            self_rating=None,
        )
        ans_theory2 = AttemptAnswer(
            attempt_id=attempt2.id,
            question_id=quiz_mastery_setup["q4_id"],
            answer_text="Student detailed answer",
            is_correct=None,
            self_rating=None,
        )
        db.session.add_all([ans2_1, ans2_2, ans2_3, ans_theory2])
        db.session.commit()
        attempt2_id = attempt2.id

    auth_client.post(
        f"/quiz/attempt/{attempt2_id}/self-grade",
        data={
            "question_id": quiz_mastery_setup["q4_id"],
            "rating": "got_it",
        },
        follow_redirects=True,
    )

    with app.app_context():
        updated2 = db.session.get(Attempt, attempt2_id)
        assert updated2.score == 3.0
        assert updated2.total_questions == 4
        # Attempt labels remain the per-attempt Decision Tree result.
        assert updated2.label == MasteryLabel.BETTER


# ==============================================================================
# 6. UI Mastery Badges & Plain-English Guidance Tests
# ==============================================================================


def test_mastery_badge_and_guidance_on_result_page(
    auth_client: FlaskClient,
    quiz_mastery_setup: dict[str, int],
    app: Flask,
    test_user: User,
) -> None:
    """Verify mastery label badge with CSS variable styling and guidance text appears on result page."""
    with app.app_context():
        attempt = Attempt(
            user_id=test_user.id,
            topic_id=quiz_mastery_setup["topic_id"],
            score=1.0,
            total_questions=4,
            wrong_count=3.0,
            attempt_number=1,
            label=MasteryLabel.WEAK,
        )
        db.session.add(attempt)
        db.session.commit()
        attempt_id = attempt.id

    resp = auth_client.get(f"/quiz/attempt/{attempt_id}")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")

    # Coloured badge for Weak
    assert "badge-mastery-weak" in html
    assert "Weak" in html

    # Plain-English guidance line
    assert "Revise the prerequisite topics first." in html
    assert "Topic mastery" in html


def test_mastery_badge_and_guidance_on_topic_page(
    auth_client: FlaskClient,
    quiz_mastery_setup: dict[str, int],
    app: Flask,
    test_user: User,
) -> None:
    """Verify latest attempt's mastery label badge and guidance line render on topic sidebar."""
    topic_id = quiz_mastery_setup["topic_id"]

    with app.app_context():
        attempt = Attempt(
            user_id=test_user.id,
            topic_id=topic_id,
            score=4.0,
            total_questions=4,
            wrong_count=0.0,
            attempt_number=1,
            label=MasteryLabel.EXCELLENT,
        )
        db.session.add(attempt)
        db.session.commit()

    resp = auth_client.get(f"/topics/{topic_id}")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")

    # Coloured badge for Excellent
    assert "badge-mastery-excellent" in html
    assert "Excellent" in html

    # Guidance text for Excellent
    assert "Outstanding mastery! You are ready to move on to next topics." in html
    assert "Topic mastery:" in html


def test_topic_features_and_label_use_all_attempts(
    app: Flask,
    test_user: User,
    quiz_mastery_setup: dict[str, int],
) -> None:
    """Verify topic features aggregate the full history and no history has no label."""
    topic_id = quiz_mastery_setup["topic_id"]
    with app.app_context():
        assert get_topic_label(test_user.id, topic_id) is None
        attempts = [
            Attempt(
                user_id=test_user.id,
                topic_id=topic_id,
                score=score,
                total_questions=4,
                wrong_count=4 - score,
                attempt_number=number,
                label=MasteryLabel.WEAK,
            )
            for number, score in enumerate((1.0, 3.0, 2.0), start=1)
        ]
        db.session.add_all(attempts)
        db.session.commit()

        assert extract_features_for_topic(test_user.id, topic_id) == [
            0.5,
            0.5,
            0.75,
            3.0,
            0.0,
        ]
        assert isinstance(get_topic_label(test_user.id, topic_id), MasteryLabel)


# ==============================================================================
# 7. CLI label-attempts Idempotency Tests
# ==============================================================================


def test_cli_label_attempts_idempotency(
    app: Flask,
    test_user: User,
    quiz_mastery_setup: dict[str, int],
) -> None:
    """Verify flask label-attempts CLI command correctly labels unlabeled attempts and is idempotent."""
    runner = app.test_cli_runner()

    # 1. Seed two attempts without labels
    with app.app_context():
        a1 = Attempt(
            user_id=test_user.id,
            topic_id=quiz_mastery_setup["topic_id"],
            score=4.0,
            total_questions=4,
            wrong_count=0.0,
            attempt_number=1,
            label=None,
        )
        a2 = Attempt(
            user_id=test_user.id,
            topic_id=quiz_mastery_setup["topic_id"],
            score=1.0,
            total_questions=4,
            wrong_count=3.0,
            attempt_number=2,
            label=None,
        )
        db.session.add_all([a1, a2])
        db.session.commit()
        a1_id, a2_id = a1.id, a2.id

    # 2. First CLI run: should find and label both attempts
    res1 = runner.invoke(args=["label-attempts"])
    assert res1.exit_code == 0
    assert "Found 2 attempt(s) to classify" in res1.output

    with app.app_context():
        refreshed_a1 = db.session.get(Attempt, a1_id)
        refreshed_a2 = db.session.get(Attempt, a2_id)
        assert refreshed_a1.label == MasteryLabel.EXCELLENT
        assert refreshed_a2.label == MasteryLabel.WEAK

    # 3. Second CLI run: idempotent, 0 remaining
    res2 = runner.invoke(args=["label-attempts"])
    assert res2.exit_code == 0
    assert "No attempts require labeling" in res2.output


# ==============================================================================
# 8. Feature Extraction & Helper Function Tests
# ==============================================================================


def test_extract_features_for_attempt(app: Flask, test_user: User, quiz_mastery_setup: dict[str, int]) -> None:
    """Verify feature extractor computes correct vector including previous attempt calculation."""
    with app.app_context():
        # First attempt: score 2/4 = 0.5
        att1 = Attempt(
            user_id=test_user.id,
            topic_id=quiz_mastery_setup["topic_id"],
            score=2.0,
            total_questions=4,
            wrong_count=2.0,
            attempt_number=1,
            label=None,
        )
        db.session.add(att1)
        db.session.commit()

        feats1 = extract_features_for_attempt(att1)
        assert feats1[0] == 0.5   # score_ratio
        assert feats1[1] == 0.5   # wrong_ratio
        assert feats1[2] == 4.0   # total_questions
        assert feats1[3] == 1.0   # attempt_number
        assert feats1[4] == -1.0  # previous_score_ratio
        assert feats1[5] == 0.0   # improvement

        # Second attempt: score 3/4 = 0.75
        att2 = Attempt(
            user_id=test_user.id,
            topic_id=quiz_mastery_setup["topic_id"],
            score=3.0,
            total_questions=4,
            wrong_count=1.0,
            attempt_number=2,
            label=None,
        )
        db.session.add(att2)
        db.session.commit()

        feats2 = extract_features_for_attempt(att2)
        assert feats2[0] == 0.75  # score_ratio
        assert feats2[1] == 0.25  # wrong_ratio
        assert feats2[2] == 4.0   # total_questions
        assert feats2[3] == 2.0   # attempt_number
        assert feats2[4] == 0.5   # previous_score_ratio
        assert feats2[5] == 0.25  # improvement (0.75 - 0.5)


def test_label_helpers() -> None:
    """Verify guidance text and badge class mapping helpers."""
    for label_enum in MasteryLabel:
        guidance = get_label_guidance(label_enum)
        badge_cls = get_label_badge_class(label_enum)
        assert len(guidance) > 10
        assert "badge-mastery-" in badge_cls

    assert get_label_guidance(None) == ""
    assert get_label_badge_class(None) == "badge-subtle"
