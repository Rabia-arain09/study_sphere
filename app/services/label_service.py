"""Topic mastery classification service.

Provides high-performance inference (<50ms) using the Decision Tree classifier,
extracts database features for attempts, handles transparent in-memory model caching
and automatic training if serialized artifacts are missing, and provides badge/guidance helpers.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
import joblib
from sklearn.tree import DecisionTreeClassifier
from app.extensions import db
from app.models.attempt import Attempt, MasteryLabel
from ml.label_model import (
    DEFAULT_MODEL_PATH,
    predict_label,
    train_model,
)

logger = logging.getLogger(__name__)

# In-memory cached model singleton (loaded once per process)
_CACHED_MODEL: DecisionTreeClassifier | None = None

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


def reset_model_cache() -> None:
    """Clear in-memory cached model singleton (used primarily in tests)."""
    global _CACHED_MODEL
    _CACHED_MODEL = None


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
            query = query.filter(Attempt.id != attempt.id)
            if attempt.created_at is not None:
                query = query.filter(Attempt.created_at <= attempt.created_at)

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
    """Classify attempt performance into a MasteryLabel enum instance.

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
