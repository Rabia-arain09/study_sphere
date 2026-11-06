"""Adaptive ranking and recommendation service for personalized student learning.

Combines curriculum knowledge graph topology (prerequisite DAG), Decision Tree mastery
classification labels, and TF-IDF topic similarities to provide tier-ranked adaptive
next-step recommendations and rerank related topics.
"""

from __future__ import annotations

import logging
from typing import Any
from sqlalchemy import func, or_
from sqlalchemy.orm import defer, joinedload

from app.extensions import db
from app.models.attempt import Attempt, MasteryLabel
from app.models.topic import Topic
from app.models.user import User
from app.services.label_service import get_user_topic_labels
from app.services.gap_analysis import (
    _parse_week,
    build_prerequisite_graph,
    traverse_prerequisites_bfs,
)

logger = logging.getLogger(__name__)


def get_user_latest_topic_attempts(user_id: int) -> dict[int, Attempt]:
    """Retrieve the user's latest Attempt instance per topic with ONE SQL query.

    Groups attempts by topic_id and joins against the maximum attempt primary key ID,
    ensuring strict user isolation and constant O(1) query count.

    Args:
        user_id: Target student user ID.

    Returns:
        dict[int, Attempt]: Mapping of topic_id -> latest Attempt record for that user.
    """
    subq = (
        db.session.query(
            Attempt.topic_id.label("topic_id"),
            func.max(Attempt.id).label("max_id"),
        )
        .filter(Attempt.user_id == user_id)
        .group_by(Attempt.topic_id)
        .subquery()
    )

    latest_attempts = (
        db.session.query(Attempt)
        .join(subq, Attempt.id == subq.c.max_id)
        .all()
    )

    return {att.topic_id: att for att in latest_attempts}


def get_next_topics(user: User, limit: int = 8) -> list[dict[str, Any]]:
    """Generate adaptive personalized topic recommendations for a student.

    Candidate topics are evaluated from the student's enrolled academic semester and
    prioritized into 5 pedagogical tiers:
        Tier 1: Prerequisite foundational gaps of user's Weak topics (deepest first).
        Tier 2: The Weak topics themselves (to retake and build mastery).
        Tier 3: Unattempted topics whose prerequisites are all non-gaps ("ready to learn"),
                ordered chronologically by course, week, and difficulty.
        Tier 4: Good and Better topics (practice to elevate to full mastery).
        Tier 5: Excellent topics last (refresher / mastered).

    Duplicates are eliminated while preserving the highest priority tier for each topic.
    Guarantees at most 3 database queries per execution, independent of the number of
    topics or historical attempts.

    Args:
        user: Enrolled student User instance.
        limit: Maximum number of recommended topics to return (default: 8).

    Returns:
        list[dict[str, Any]]: Ordered list of recommended topic dicts containing:
            - id (int): Topic primary key
            - topic_id (int): Alias topic primary key
            - name (str): Topic title
            - course (str): Associated course title
            - course_name (str): Associated course title alias
            - difficulty (int): Difficulty rating (1-5)
            - label (str): Aggregate topic mastery label or "Not attempted"
            - reason (str): Plain-English pedagogical rationale
            - tier (int): Priority tier rank (1-5)
    """
    if user is None:
        return []

    # Query 1: Single batched query for user's latest attempt per topic
    attempts_by_topic = get_user_latest_topic_attempts(user.id)
    topic_labels = get_user_topic_labels(user.id)

    # Query 2: Single query loading curriculum prerequisite DAG edges
    adj = build_prerequisite_graph()

    # In-memory identification of weak topics for this user
    weak_topic_ids_all: set[int] = {
        topic_id
        for topic_id, label in topic_labels.items()
        if label == MasteryLabel.WEAK
    }

    # Identify prerequisite gaps of weak topics via BFS (Tier 1)
    # Track max depth and parent weak topic for each gap
    prereq_gaps_meta: dict[int, dict[str, Any]] = {}
    for wt_id in weak_topic_ids_all:
        depths = traverse_prerequisites_bfs(wt_id, adj, max_depth=4)
        for prereq_id, depth in depths.items():
            att = attempts_by_topic.get(prereq_id)
            label = topic_labels.get(prereq_id)
            # A visited prerequisite is a gap if unattempted or Weak
            if att is None or label == MasteryLabel.WEAK:
                if prereq_id not in prereq_gaps_meta or depth > prereq_gaps_meta[prereq_id]["depth"]:
                    prereq_gaps_meta[prereq_id] = {
                        "depth": depth,
                        "weak_topic_id": wt_id,
                        "status": (
                            "Weak"
                            if label == MasteryLabel.WEAK
                            else "Not attempted"
                        ),
                    }

    # Query 3: Fetch all semester topics and any external prerequisite gap topics in ONE query
    gap_ids = list(prereq_gaps_meta.keys())
    candidate_filter = (
        Topic.semester == user.semester
        if not gap_ids
        else or_(Topic.semester == user.semester, Topic.id.in_(gap_ids))
    )

    topic_rows = (
        Topic.query.options(
            joinedload(Topic.course),
            defer(Topic.content),
        )
        .filter(candidate_filter)
        .all()
    )
    topic_map: dict[int, Topic] = {t.id: t for t in topic_rows}

    # Helper function to format topic dictionary
    def _format_item(
        t: Topic,
        lbl: str,
        reason: str,
        tier: int,
        depth: int = 0,
    ) -> dict[str, Any]:
        course_name = t.course.title if t.course else t.subject
        return {
            "id": t.id,
            "topic_id": t.id,
            "name": t.name,
            "course": course_name,
            "course_name": course_name,
            "difficulty": t.difficulty,
            "week": t.week,
            "label": lbl,
            "reason": reason,
            "tier": tier,
            "depth": depth,
        }

    # Partition topics into Priority Tiers
    tier_1_items: list[dict[str, Any]] = []
    tier_2_items: list[dict[str, Any]] = []
    tier_3_items: list[dict[str, Any]] = []
    tier_4_items: list[dict[str, Any]] = []
    tier_5_items: list[dict[str, Any]] = []

    # Tier 1: Prerequisite gaps of Weak topics (deepest first)
    for gap_id, meta in prereq_gaps_meta.items():
        t = topic_map.get(gap_id)
        if t is not None:
            parent_wt = topic_map.get(meta["weak_topic_id"])
            parent_name = parent_wt.name if parent_wt else "a topic"
            reason=f"Prerequisite of {parent_name}, which has Weak topic mastery"
            tier_1_items.append(
                _format_item(
                    t=t,
                    lbl=meta["status"],
                    reason=reason,
                    tier=1,
                    depth=meta["depth"],
                )
            )

    # Sort Tier 1: deepest first (-depth), ties by difficulty, then week, then id
    tier_1_items.sort(
        key=lambda x: (
            -x["depth"],
            x["difficulty"],
            _parse_week(x["week"]),
            x["id"],
        )
    )

    # Filter semester topics for Tiers 2-5
    semester_topic_rows = [t for t in topic_rows if t.semester == user.semester]

    for t in semester_topic_rows:
        att = attempts_by_topic.get(t.id)
        topic_label = topic_labels.get(t.id)
        lbl = topic_label.value if topic_label else "Not attempted"

        if lbl == MasteryLabel.WEAK.value or lbl == "Weak":
            # Tier 2: The Weak topics themselves (to retake)
            tier_2_items.append(
                _format_item(
                    t=t,
                    lbl="Weak",
                    reason="Topic mastery is Weak — retake to build mastery",
                    tier=2,
                )
            )
        elif att is None or lbl == "Not attempted":
            # Tier 3: Unattempted topics whose prerequisites are all non-gaps ("ready to learn")
            # Check if all visited prerequisites in DAG are non-gaps (attempted & not Weak)
            prereq_depths = traverse_prerequisites_bfs(t.id, adj, max_depth=4)
            has_gap = False
            for p_id in prereq_depths:
                p_att = attempts_by_topic.get(p_id)
                p_label = topic_labels.get(p_id)
                if p_att is None or p_label == MasteryLabel.WEAK:
                    has_gap = True
                    break

            if not has_gap:
                tier_3_items.append(
                    _format_item(
                        t=t,
                        lbl="Not attempted",
                        reason="Ready to learn — all prerequisites met",
                        tier=3,
                    )
                )
        elif lbl in (MasteryLabel.GOOD.value, MasteryLabel.BETTER.value, "Good", "Better"):
            # Tier 4: Good and Better topics (practice)
            tier_4_items.append(
                _format_item(
                    t=t,
                    lbl=lbl,
                    reason=f"Scored {lbl} — practice to reach mastery",
                    tier=4,
                )
            )
        elif lbl == MasteryLabel.EXCELLENT.value or lbl == "Excellent":
            # Tier 5: Excellent topics last
            tier_5_items.append(
                _format_item(
                    t=t,
                    lbl="Excellent",
                    reason="Mastered (Excellent) — review or refresh",
                    tier=5,
                )
            )

    # Sort remaining tiers
    tier_2_items.sort(
        key=lambda x: (
            x["difficulty"],
            _parse_week(x["week"]),
            x["name"],
        )
    )
    # Tier 3: ordered by course, week, difficulty
    tier_3_items.sort(
        key=lambda x: (
            x["course"],
            _parse_week(x["week"]),
            x["difficulty"],
            x["name"],
        )
    )
    # Tier 4: Good before Better, then difficulty, week
    tier_4_items.sort(
        key=lambda x: (
            0 if x["label"] == "Good" else 1,
            x["difficulty"],
            _parse_week(x["week"]),
            x["name"],
        )
    )
    # Tier 5: difficulty ascending, week ascending
    tier_5_items.sort(
        key=lambda x: (
            x["difficulty"],
            _parse_week(x["week"]),
            x["name"],
        )
    )

    # Deduplicate while preserving best tier order
    seen_ids: set[int] = set()
    result: list[dict[str, Any]] = []

    for item in tier_1_items + tier_2_items + tier_3_items + tier_4_items + tier_5_items:
        if item["id"] not in seen_ids:
            seen_ids.add(item["id"])
            result.append(item)
            if len(result) >= limit:
                break

    return result


def rerank_related(
    user: User | None,
    related_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Rerank a content-based related topics list using adaptive student mastery tiers.

    Re-orders recommendations using the pedagogical tier concept:
        - Tier 1: Prerequisite foundational gaps of user's Weak topics.
        - Tier 2: Weak topics themselves.
        - Tier 3: Topics not yet attempted.
        - Tier 4: Good and Better topics (practice).
        - Tier 5: Mastered (Excellent) topics last (not removed).

    Uses TF-IDF cosine similarity score as the tie-breaker within each tier.
    Attaches the student's mastery label ("Weak", "Good", "Better", "Excellent", or "Not attempted")
    to each returned dictionary.

    Args:
        user: Currently authenticated student User or None.
        related_items: List of related topic dictionaries from recommendation_service.

    Returns:
        list[dict[str, Any]]: Reordered list of topic dictionaries with "label" attached.
    """
    if not related_items:
        return []

    # If unauthenticated, attach "Not attempted" and retain original similarity ordering
    if user is None or not getattr(user, "is_authenticated", True):
        out: list[dict[str, Any]] = []
        for it in related_items:
            copied = dict(it)
            copied.setdefault("label", "Not attempted")
            out.append(copied)
        return out

    # 1. User latest attempts in ONE query
    attempts_by_topic = get_user_latest_topic_attempts(user.id)
    topic_labels = get_user_topic_labels(user.id)

    # 2. Prerequisite graph in ONE query
    adj = build_prerequisite_graph()

    # Identify prerequisite gaps of weak topics
    weak_topic_ids: set[int] = {
        topic_id
        for topic_id, label in topic_labels.items()
        if label == MasteryLabel.WEAK
    }

    prereq_gaps_of_weak: set[int] = set()
    for wt_id in weak_topic_ids:
        depths = traverse_prerequisites_bfs(wt_id, adj, max_depth=4)
        for p_id in depths:
            att = attempts_by_topic.get(p_id)
            label = topic_labels.get(p_id)
            if att is None or label == MasteryLabel.WEAK:
                prereq_gaps_of_weak.add(p_id)

    annotated: list[tuple[int, float, dict[str, Any]]] = []
    for item in related_items:
        tid = item["id"]
        topic_label = topic_labels.get(tid)
        lbl = topic_label.value if topic_label else "Not attempted"

        # Determine Tier
        if tid in prereq_gaps_of_weak:
            tier = 1
        elif lbl == MasteryLabel.WEAK.value or lbl == "Weak":
            tier = 2
        elif lbl == "Not attempted":
            tier = 3
        elif lbl in (MasteryLabel.GOOD.value, MasteryLabel.BETTER.value, "Good", "Better"):
            tier = 4
        elif lbl == MasteryLabel.EXCELLENT.value or lbl == "Excellent":
            tier = 5
        else:
            tier = 3

        item_copy = dict(item)
        item_copy["label"] = lbl
        sim_score = float(item.get("score", 0.0))
        annotated.append((tier, sim_score, item_copy))

    # Sort primarily by tier ascending, secondarily by similarity score descending
    annotated.sort(key=lambda t: (t[0], -t[1]))

    return [item[2] for item in annotated]
