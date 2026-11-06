"""Per-attempt and aggregate topic mastery classification services.

Provides cached Decision Tree inference, extracts attempt-history features, trains missing
model artifacts, and provides badge/guidance helpers.
"""

from __future__ import annotations

import logging
from pathlib import Path
import joblib
from sklearn.tree import DecisionTreeClassifier
from app.extensions import db
from app.models.attempt import Attempt, MasteryLabel
from ml.label_model import (
    DEFAULT_MODEL_PATH,
    DEFAULT_TOPIC_MODEL_PATH,
    predict_label,
    predict_topic_label,
    train_model,
    train_topic_model,
)

logger = logging.getLogger(__name__)

# In-memory cached model singleton (loaded once per process)
_CACHED_MODEL: DecisionTreeClassifier | None = None
_CACHED_TOPIC_MODEL: DecisionTreeClassifier | None = None

# Plain-English guidance lines corresponding to each mastery tier
LABEL_GUIDANCE: dict[str, str] = {
    MasteryLabel.WEAK.value: "Revise the prerequisite topics first.",
    MasteryLabel.GOOD.value: "Solid foundation. Review incorrect questions to strengthen concepts.",
    MasteryLabel.BETTER.value: "Strong understanding! Practice advanced problems to master this topic.",
    MasteryLabel.EXCELLENT.value: "Outstanding mastery! You are ready to move on to next topics.",
}

# CSS badge styling mapping using system CSS variables
LABEL_BADGE_CLASSES: dict[str, str] = {
    MasteryLabel.WEAK.value: "badge-mastery-weak",
    MasteryLabel.GOOD.value: "badge-mastery-good",
    MasteryLabel.BETTER.value: "badge-mastery-better",
    MasteryLabel.EXCELLENT.value: "badge-mastery-excellent",
}


def get_model(
    model_path: Path | str | None = None,
    force_reload: bool = False,
) -> DecisionTreeClassifier:
    """Retrieve or initialize the Decision Tree model singleton.

    Loads the saved model once per process; if the serialized artifact is missing,
    automatically triggers synthetic dataset generation and model training with seed=42,
    persisting the resulting model artifact so teammates and tests require zero manual setup.

    Args:
        model_path: Optional custom path to model joblib artifact.
        force_reload: If True, bypasses memory cache and reloads from disk or trains.

    Returns:
        DecisionTreeClassifier: Ready-to-use scikit-learn model.
    """
    global _CACHED_MODEL
    if _CACHED_MODEL is not None and not force_reload and model_path is None:
        return _CACHED_MODEL

    target_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH

    if not target_path.exists():
        logger.info(
            "Model artifact %s not found. Initiating automatic training with seed=42...",
            target_path,
        )
        training_result = train_model(seed=42, model_path=target_path)
        model: DecisionTreeClassifier = training_result["model"]
    else:
        logger.debug("Loading cached Decision Tree model from %s", target_path)
        model = joblib.load(target_path)

    if model_path is None:
        _CACHED_MODEL = model
    return model


def get_topic_model(force_reload: bool = False) -> DecisionTreeClassifier:
    """Load or train the aggregate topic mastery model once per process."""
    global _CACHED_TOPIC_MODEL
    if _CACHED_TOPIC_MODEL is not None and not force_reload:
        return _CACHED_TOPIC_MODEL

    if not DEFAULT_TOPIC_MODEL_PATH.exists():
        logger.info(
            "Topic mastery model artifact %s not found; training it now.",
            DEFAULT_TOPIC_MODEL_PATH,
        )
        model = train_topic_model(seed=42)["model"]
    else:
        model = joblib.load(DEFAULT_TOPIC_MODEL_PATH)

    _CACHED_TOPIC_MODEL = model
    return model


def reset_model_cache() -> None:
    """Clear in-memory cached model singleton (used primarily in tests)."""
    global _CACHED_MODEL, _CACHED_TOPIC_MODEL
    _CACHED_MODEL = None
    _CACHED_TOPIC_MODEL = None


def extract_features_for_attempt(
    attempt: Attempt,
    prev_attempt: Attempt | None = None,
) -> list[float]:
    """Build the 6 numerical features required by the Decision Tree classifier from database state.

    Features:
    1. score_ratio: attempt.score / attempt.total_questions (0.0 if empty).
    2. wrong_ratio: attempt.wrong_count / attempt.total_questions (0.0 if empty).
    3. total_questions: attempt.total_questions as float.
    4. attempt_number: attempt.attempt_number capped at 5.
    5. previous_score_ratio: score ratio of the same user's previous attempt on the topic (-1.0 if none).
    6. improvement: score_ratio - previous_score_ratio (0.0 if no previous attempt).

    Uses a single indexed query against `ix_attempts_user_id_topic_id` if prev_attempt is not supplied.

    Args:
        attempt: The target Attempt model instance.
        prev_attempt: Optional explicitly supplied previous attempt (avoids query if known).

    Returns:
        list[float]: Vector of 6 float features.
    """
    score_ratio = (
        float(attempt.score / attempt.total_questions)
        if attempt.total_questions > 0
        else 0.0
    )
    wrong_ratio = (
        float(attempt.wrong_count / attempt.total_questions)
        if attempt.total_questions > 0
        else 0.0
    )
    total_q = float(attempt.total_questions)
    attempt_num = float(min(attempt.attempt_number, 5))

    # Single indexed query to find the previous attempt of the same user and topic
    if prev_attempt is None:
        query = Attempt.query.filter(
            Attempt.user_id == attempt.user_id,
            Attempt.topic_id == attempt.topic_id,
        )
        if attempt.id is not None:
            query = query.filter(Attempt.id < attempt.id)
        elif attempt.created_at is not None:
            query = query.filter(Attempt.created_at < attempt.created_at)

        prev_attempt = query.order_by(Attempt.id.desc()).first()

    if prev_attempt is not None and prev_attempt.total_questions > 0:
        prev_score_ratio = float(prev_attempt.score / prev_attempt.total_questions)
        improvement = float(score_ratio - prev_score_ratio)
    else:
        prev_score_ratio = -1.0
        improvement = 0.0

    return [
        score_ratio,
        wrong_ratio,
        total_q,
        attempt_num,
        prev_score_ratio,
        improvement,
    ]


def predict_mastery_for_attempt(
    attempt: Attempt,
    prev_attempt: Attempt | None = None,
) -> MasteryLabel:
    """Classify one attempt into a MasteryLabel enum instance.

    Execution time is well under 50 ms (in-memory tree inference takes < 1 ms).

    Args:
        attempt: Target Attempt instance.
        prev_attempt: Optional explicitly supplied previous attempt.

    Returns:
        MasteryLabel: WEAK, GOOD, BETTER, or EXCELLENT enum member.
    """
    features = extract_features_for_attempt(attempt, prev_attempt=prev_attempt)
    model = get_model()
    raw_label = predict_label(features, model=model)
    return MasteryLabel(raw_label)


def _features_from_topic_attempts(attempts: list[Attempt]) -> list[float] | None:
    """Calculate aggregate topic features from chronologically ordered attempts."""
    if not attempts:
        return None

    ordered_attempts = sorted(attempts, key=lambda attempt: attempt.id or 0)
    score_ratios = [
        float(attempt.score / attempt.total_questions)
        if attempt.total_questions > 0
        else 0.0
        for attempt in ordered_attempts
    ]
    average_ratio = sum(score_ratios) / len(score_ratios)
    latest_ratio = score_ratios[-1]
    return [
        average_ratio,
        latest_ratio,
        max(score_ratios),
        float(len(score_ratios)),
        latest_ratio - average_ratio,
    ]


def extract_features_for_topic(
    user_id: int,
    topic_id: int,
) -> list[float] | None:
    """Build average, latest, best, count, and trend features from topic attempts."""
    attempts = (
        Attempt.query.filter_by(user_id=user_id, topic_id=topic_id)
        .order_by(Attempt.id.asc())
        .all()
    )
    return _features_from_topic_attempts(attempts)


def predict_topic_labels_from_attempts(
    attempts_by_topic: dict[int, list[Attempt]],
) -> dict[int, MasteryLabel]:
    """Predict topic labels in one model call from grouped user attempt histories."""
    feature_rows = {
        topic_id: features
        for topic_id, attempts in attempts_by_topic.items()
        if (features := _features_from_topic_attempts(attempts)) is not None
    }
    if not feature_rows:
        return {}

    model = get_topic_model()
    predictions = model.predict(list(feature_rows.values()))
    return {
        topic_id: MasteryLabel(str(prediction))
        for topic_id, prediction in zip(feature_rows, predictions)
    }


def get_user_topic_labels(
    user_id: int,
    topic_ids: list[int] | None = None,
) -> dict[int, MasteryLabel]:
    """Return aggregate-model labels for all attempted topics belonging to a user."""
    query = Attempt.query.filter(Attempt.user_id == user_id)
    if topic_ids is not None:
        if not topic_ids:
            return {}
        query = query.filter(Attempt.topic_id.in_(topic_ids))

    attempts_by_topic: dict[int, list[Attempt]] = {}
    for attempt in query.order_by(Attempt.topic_id.asc(), Attempt.id.asc()).all():
        attempts_by_topic.setdefault(attempt.topic_id, []).append(attempt)
    return predict_topic_labels_from_attempts(attempts_by_topic)


def get_topic_label(user_id: int, topic_id: int) -> MasteryLabel | None:
    """Return the trained topic-level mastery label, or None without attempts."""
    features = extract_features_for_topic(user_id, topic_id)
    if features is None:
        return None
    return MasteryLabel(predict_topic_label(features, model=get_topic_model()))


def label_attempt_record(
    attempt: Attempt,
    prev_attempt: Attempt | None = None,
    commit: bool = False,
) -> MasteryLabel:
    """Compute and assign mastery label on an Attempt instance.

    Args:
        attempt: Target Attempt model instance.
        prev_attempt: Optional prior attempt.
        commit: Whether to commit changes to the database session immediately.

    Returns:
        MasteryLabel: The assigned enum label.
    """
    label = predict_mastery_for_attempt(attempt, prev_attempt=prev_attempt)
    attempt.label = label
    if commit:
        db.session.commit()
    return label


def get_label_guidance(label: MasteryLabel | str | None) -> str:
    """Return plain-English pedagogical guidance for a mastery label.

    Args:
        label: MasteryLabel enum member, label string, or None.

    Returns:
        str: Actionable study advice for the student.
    """
    if label is None:
        return ""
    val = label.value if isinstance(label, MasteryLabel) else str(label)
    return LABEL_GUIDANCE.get(val, "")


def get_label_badge_class(label: MasteryLabel | str | None) -> str:
    """Return CSS class name for rendering a mastery label badge.

    Args:
        label: MasteryLabel enum member, label string, or None.

    Returns:
        str: CSS class name corresponding to badge theme.
    """
    if label is None:
        return "badge-subtle"
    val = label.value if isinstance(label, MasteryLabel) else str(label)
    return LABEL_BADGE_CLASSES.get(val, "badge-subtle")
