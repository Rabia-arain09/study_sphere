"""Prerequisite knowledge gap analysis service.

Performs pure Python breadth-first search (BFS) graph traversal over the
curriculum topic prerequisite DAG to identify foundational knowledge deficits
(unattempted or Weak prerequisites) for personalized student remediation.
"""

from __future__ import annotations

import collections
import re
from typing import Any
from sqlalchemy import func
from sqlalchemy.orm import defer, joinedload

from app.extensions import db
from app.models.attempt import Attempt, MasteryLabel
from app.models.prerequisite import Prerequisite
from app.models.topic import Topic


class GapList(list):
    """Custom list subclass preserving list semantics while holding prerequisite metadata."""

    def __init__(
        self,
        items: list[dict[str, Any]] | None = None,
        has_prerequisites: bool = False,
    ) -> None:
        super().__init__(items or [])
        self.has_prerequisites = has_prerequisites


def _parse_week(week: str | None) -> int:
    """Extract primary academic week number for deterministic chronological sorting.

    Args:
        week: Raw week indicator string (e.g., '1', '2-3', 'Week 4') or None.

    Returns:
        int: Start week integer, or 999 for unassigned/missing week values.
    """
    if not week:
        return 999
    nums = re.findall(r"\d+", str(week))
    return int(nums[0]) if nums else 999


def build_prerequisite_graph() -> dict[int, list[int]]:
    """Load all prerequisite edges in ONE single query and build adjacency mapping.

    Returns:
        dict[int, list[int]]: Adjacency mapping from topic_id -> list of prerequisite_topic_ids.
    """
    edges = db.session.query(
        Prerequisite.topic_id, Prerequisite.prerequisite_topic_id
    ).all()

    adj: dict[int, list[int]] = {}
    for tid, prereq_id in edges:
        adj.setdefault(tid, []).append(prereq_id)
    return adj


def traverse_prerequisites_bfs(
    start_topic_id: int,
    adj: dict[int, list[int]],
    max_depth: int = 4,
) -> dict[int, int]:
    """Traverse backward through prerequisites via BFS up to max_depth with cycle safety.

    Args:
        start_topic_id: Root topic ID to start traversal from.
        adj: Adjacency dictionary mapping topic_id -> list of prerequisite_topic_ids.
        max_depth: Maximum recursion/traversal depth (default: 4).

    Returns:
        dict[int, int]: Visited prerequisite topic IDs mapped to their minimum traversal depth.
    """
    visited: set[int] = {start_topic_id}
    queue: collections.deque[tuple[int, int]] = collections.deque([(start_topic_id, 0)])
    depths: dict[int, int] = {}

    while queue:
        curr_id, curr_depth = queue.popleft()
        if curr_depth >= max_depth:
            continue

        for prereq_id in adj.get(curr_id, []):
            if prereq_id not in visited:
                visited.add(prereq_id)
                depths[prereq_id] = curr_depth + 1
                queue.append((prereq_id, curr_depth + 1))

    return depths


def get_prerequisite_gaps(
    topic_id: int,
    user_id: int,
    max_depth: int = 4,
    limit: int = 10,
) -> GapList:
    """Analyze foundational knowledge gaps for a user on a given topic.

    Steps:
    1. Load all prerequisite edges with ONE query and build in-memory adjacency dict.
    2. Walk back from given topic through its prerequisites (BFS, max_depth 4, cycle-safe).
    3. Query user's latest attempt per visited topic with ONE query (max attempt ID per topic).
    4. Flag visited topics as gaps if latest label is Weak or if unattempted.
       (Good, Better, and Excellent are not gaps, but the walk continues through them).
    5. Fetch topic entities with ONE query (joinedload course, defer content).
    6. Return gaps ordered: deeper prerequisites first (-depth), ties by difficulty, then week.

    Total DB queries per call: at most 3 (or 4 including target topic validation), constant.

    Args:
        topic_id: Target topic ID to inspect prerequisites for.
        user_id: ID of the current student to isolate attempt data.
        max_depth: Max depth of prerequisite traversal (default 4).
        limit: Max number of gap items to return (default 10).

    Returns:
        GapList: List of gap dictionaries with attributes:
            - topic_id (int)
            - id (int)
            - name (str)
            - course_name (str)
            - course (str)
            - status (str: "Weak" or "Not attempted")
            - depth (int)
            - latest_percentage (float | None)
    """
    # 1. Load all edges in ONE query
    adj = build_prerequisite_graph()

    # Check if topic has any direct prerequisites in the graph
    direct_prereqs = adj.get(topic_id, [])
    if not direct_prereqs:
        return GapList([], has_prerequisites=False)

    # 2. BFS traversal (max depth 4, cycle-safe with visited set)
    depths = traverse_prerequisites_bfs(topic_id, adj, max_depth=max_depth)
    visited_topic_ids = list(depths.keys())
    if not visited_topic_ids:
        return GapList([], has_prerequisites=True)

    # 3. Query user's latest attempt per visited topic with ONE query
    subq = (
        db.session.query(
            Attempt.topic_id.label("topic_id"),
            func.max(Attempt.id).label("max_id"),
        )
        .filter(
            Attempt.user_id == user_id,
            Attempt.topic_id.in_(visited_topic_ids),
        )
        .group_by(Attempt.topic_id)
        .subquery()
    )

    latest_attempts = (
        db.session.query(Attempt)
        .join(subq, Attempt.id == subq.c.max_id)
        .all()
    )

    attempts_by_topic: dict[int, Attempt] = {att.topic_id: att for att in latest_attempts}

    # 4. Identify gaps (Weak or Not attempted)
    gaps_metadata: dict[int, dict[str, Any]] = {}
    for tid in visited_topic_ids:
        attempt = attempts_by_topic.get(tid)
        if attempt is None:
            # Never attempted -> Gap!
            gaps_metadata[tid] = {
                "status": "Not attempted",
                "latest_percentage": None,
            }
        else:
            lbl_val = (
                attempt.label.value if hasattr(attempt.label, "value") else str(attempt.label)
            ) if attempt.label else None

            if lbl_val == MasteryLabel.WEAK.value or lbl_val == "Weak":
                pct = (
                    round((attempt.score / attempt.total_questions * 100.0), 1)
                    if attempt.total_questions > 0
                    else 0.0
                )
                gaps_metadata[tid] = {
                    "status": "Weak",
                    "latest_percentage": pct,
                }
            # Good, Better, Excellent: not gaps!

    if not gaps_metadata:
        return GapList([], has_prerequisites=True)

    # 5. Fetch topic rows with ONE query (joinedload course, defer content)
    gap_topic_ids = list(gaps_metadata.keys())
    topic_rows = (
        Topic.query.options(
            joinedload(Topic.course),
            defer(Topic.content),
        )
        .filter(Topic.id.in_(gap_topic_ids))
        .all()
    )

    # 6. Order gaps: deeper prerequisites first (-depth), ties by difficulty, then week
    sorted_topics = sorted(
        topic_rows,
        key=lambda t: (-depths[t.id], t.difficulty, _parse_week(t.week), t.id),
    )

    items: list[dict[str, Any]] = []
    for t in sorted_topics[:limit]:
        course_name = t.course.title if t.course else t.subject
        meta = gaps_metadata[t.id]
        items.append({
            "topic_id": t.id,
            "id": t.id,
            "name": t.name,
            "course_name": course_name,
            "course": course_name,
            "status": meta["status"],
            "depth": depths[t.id],
            "latest_percentage": meta["latest_percentage"],
        })

    return GapList(items, has_prerequisites=True)


# Helpful aliases
find_prerequisite_gaps = get_prerequisite_gaps
analyze_gaps = get_prerequisite_gaps
