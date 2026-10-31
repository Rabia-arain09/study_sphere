"""Recommendation service managing in-memory TopicRecommender lifecycle and querying."""

from __future__ import annotations

import logging
import threading
from typing import Any
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from app.extensions import db
from app.models.topic import Topic
from ml.recommender import TopicRecommender

logger = logging.getLogger(__name__)

# Module-level thread-safe in-memory cache
_recommender_lock = threading.Lock()
_cached_recommender: TopicRecommender | None = None
_cached_state_key: tuple[Any, ...] | None = None


def get_db_state_key() -> tuple[Any, ...]:
    """Compute a lightweight database state key to detect topic additions or content changes.

    Inspects total topic count, maximum topic primary key, and aggregate content
    length / updated timestamp to determine if the in-memory TF-IDF index is stale.

    Returns:
        tuple[Any, ...]: Hashable state key representing current topic data state.
    """
    if hasattr(Topic, "updated_at"):
        row = db.session.query(
            func.count(Topic.id),
            func.max(Topic.id),
            func.max(getattr(Topic, "updated_at")),
        ).first()
        return (row[0] or 0, row[1] or 0, str(row[2]) if row and row[2] else "")

    row = db.session.query(
        func.count(Topic.id),
        func.max(Topic.id),
        func.coalesce(func.sum(func.length(Topic.content)), 0),
    ).first()
    return (row[0] or 0, row[1] or 0, int(row[2] or 0) if row else 0)


def get_recommender(force_rebuild: bool = False) -> TopicRecommender:
    """Lazily initialize or refresh the in-memory TopicRecommender instance.

    Loads only required columns (id, name, description, tags, content, subject)
    from the database and fits the TF-IDF vectorizer when uninitialized or when
    database state changes.

    Args:
        force_rebuild: Whether to bypass cache and force re-fitting from database.

    Returns:
        TopicRecommender: Active fitted recommender singleton.
    """
    global _cached_recommender, _cached_state_key

    with _recommender_lock:
        current_state = get_db_state_key()

        if (
            not force_rebuild
            and _cached_recommender is not None
            and _cached_state_key == current_state
        ):
            return _cached_recommender

        logger.info(
            "Building topic recommendation index (state=%s, force=%s)...",
            current_state,
            force_rebuild,
        )

        # Load only required columns to minimize memory footprint and database query time
        topic_rows = (
            db.session.query(
                Topic.id,
                Topic.name,
                Topic.description,
                Topic.tags,
                Topic.content,
                Topic.subject,
            )
            .order_by(Topic.id)
            .all()
        )

        recommender = TopicRecommender(same_subject_boost=0.05)
        recommender.fit(topic_rows)

        _cached_recommender = recommender
        _cached_state_key = current_state
        return _cached_recommender


def reset_recommender() -> None:
    """Clear in-memory recommender cache (primarily used in test fixtures)."""
    global _cached_recommender, _cached_state_key
    with _recommender_lock:
        _cached_recommender = None
        _cached_state_key = None


def get_recommendations(topic_id: int, k: int = 5) -> list[tuple[int, float]]:
    """Retrieve raw recommended topic IDs and similarity scores.

    Args:
        topic_id: Query topic ID.
        k: Maximum number of recommendations to retrieve.

    Returns:
        list[tuple[int, float]]: List of (topic_id, score) tuples.
    """
    recommender = get_recommender()
    return recommender.recommend(topic_id=topic_id, k=k)


def get_related_topics(topic_id: int, k: int = 5) -> list[dict[str, Any]]:
    """Retrieve full metadata for related topics using a single batched SQL query.

    Args:
        topic_id: Query topic ID.
        k: Maximum number of recommendations to retrieve (default: 5).

    Returns:
        list[dict[str, Any]]: Formatted list of topic dictionaries with keys:
        {id, name, course, week, difficulty, score}.
    """
    recs = get_recommendations(topic_id=topic_id, k=k)
    if not recs:
        return []

    rec_ids = [item[0] for item in recs]

    # Single batched SQL query fetching all recommended topics with course joined
    topics = (
        Topic.query.options(joinedload(Topic.course))
        .filter(Topic.id.in_(rec_ids))
        .all()
    )
    topic_map = {topic.id: topic for topic in topics}

    results: list[dict[str, Any]] = []
    for rec_id, score in recs:
        t = topic_map.get(rec_id)
        if t is not None:
            course_title = t.course.title if t.course else t.subject
            results.append({
                "id": t.id,
                "name": t.name,
                "course": course_title,
                "week": t.week,
                "difficulty": t.difficulty,
                "score": round(score, 4),
            })

    return results
