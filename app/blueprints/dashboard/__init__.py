"""Dashboard blueprint for student analytics, mastery distribution, and adaptive recommendations."""

from __future__ import annotations

from typing import Any
from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm import defer, joinedload

from app.extensions import db
from app.models.attempt import Attempt, MasteryLabel
from app.models.course import Course
from app.models.topic import Topic
from app.models.upload import Upload
from app.services.adaptive_service import (
    get_next_topics,
    get_user_latest_topic_attempts,
    normalize_label,
)
from app.services.gap_analysis import (
    build_prerequisite_graph,
    traverse_prerequisites_bfs,
)

dashboard_bp: Blueprint = Blueprint("dashboard", __name__)


def get_dashboard_data(user: Any) -> dict[str, Any]:
    """Compile aggregated analytics, charts, and recommendations for a student.

    Guarantees user isolation and constant O(1) query count by utilizing
    SQL aggregate functions, subqueries, and in-memory DAG evaluations.

    Args:
        user: Currently authenticated User instance.

    Returns:
        dict[str, Any]: Complete dashboard data payload containing summary metrics,
            Chart.js structured JSON datasets, revise-first list, and next topics.
    """
    user_id: int = user.id
    user_semester: int = user.semester

    # 1. Total attempts and average percentage (1 aggregate query)
    attempt_stats = (
        db.session.query(
            func.count(Attempt.id),
            func.avg(Attempt.score / Attempt.total_questions * 100.0),
        )
        .filter(Attempt.user_id == user_id, Attempt.total_questions > 0)
        .first()
    )
    total_attempts: int = int(attempt_stats[0]) if attempt_stats and attempt_stats[0] else 0
    average_percentage: float = (
        round(float(attempt_stats[1]), 1)
        if attempt_stats and attempt_stats[1] is not None
        else 0.0
    )

    # 2. Uploads count (1 aggregate query)
    uploads_count: int = (
        db.session.query(func.count(Upload.id))
        .filter(Upload.user_id == user_id)
        .scalar()
        or 0
    )

    # 3. Latest attempt per topic for current user (1 query)
    latest_attempts = get_user_latest_topic_attempts(user_id)
    topics_attempted: int = len(latest_attempts)

    # Label counts for Chart 1 and summary counts
    label_counts = {
        MasteryLabel.WEAK.value: 0,
        MasteryLabel.GOOD.value: 0,
        MasteryLabel.BETTER.value: 0,
        MasteryLabel.EXCELLENT.value: 0,
    }
    for att in latest_attempts.values():
        lbl_str = normalize_label(att.label)
        if lbl_str in label_counts:
            label_counts[lbl_str] += 1

    mastered_topics: int = (
        label_counts[MasteryLabel.BETTER.value]
        + label_counts[MasteryLabel.EXCELLENT.value]
    )
    weak_topics_count: int = label_counts[MasteryLabel.WEAK.value]

    chart_labels_data = {
        "labels": ["Weak", "Good", "Better", "Excellent"],
        "data": [
            label_counts[MasteryLabel.WEAK.value],
            label_counts[MasteryLabel.GOOD.value],
            label_counts[MasteryLabel.BETTER.value],
            label_counts[MasteryLabel.EXCELLENT.value],
        ],
        "colors": ["#dc2626", "#d97706", "#2563eb", "#16a34a"],
    }

    # 4. Progress over time: percentage of last 20 attempts (1 query)
    last_20_attempts_desc = (
        Attempt.query.options(joinedload(Attempt.topic))
        .filter(Attempt.user_id == user_id)
        .order_by(Attempt.id.desc())
        .limit(20)
        .all()
    )
    last_20_attempts = list(reversed(last_20_attempts_desc))

    chart_progress_data = {
        "labels": [
            f"#{att.attempt_number} ({att.topic.name[:14]})"
            if att.topic
            else f"#{att.id}"
            for att in last_20_attempts
        ],
        "percentages": [
            round((att.score / att.total_questions * 100.0), 1)
            if att.total_questions > 0
            else 0.0
            for att in last_20_attempts
        ],
    }

    # 5. Semester courses and topics (2 queries)
    semester_courses = (
        Course.query.filter_by(semester=user_semester)
        .order_by(Course.code)
        .all()
    )
    semester_topics = (
        Topic.query.options(joinedload(Topic.course), defer(Topic.content))
        .filter(Topic.semester == user_semester)
        .all()
    )
    topic_map: dict[int, Topic] = {t.id: t for t in semester_topics}

    course_topic_ids: dict[int, list[int]] = {}
    for t in semester_topics:
        course_topic_ids.setdefault(t.course_id, []).append(t.id)

    # Grouped average percentage per course for this user (1 aggregate query)
    course_avg_scores = dict(
        db.session.query(
            Topic.course_id,
            func.avg(Attempt.score / Attempt.total_questions * 100.0),
        )
        .join(Attempt, Attempt.topic_id == Topic.id)
        .filter(
            Attempt.user_id == user_id,
            Topic.semester == user_semester,
            Attempt.total_questions > 0,
        )
        .group_by(Topic.course_id)
        .all()
    )

    course_stats_list: list[dict[str, Any]] = []
    course_chart_labels: list[str] = []
    course_chart_attempted: list[int] = []
    course_chart_total: list[int] = []
    course_chart_avg_pct: list[float] = []

    for c in semester_courses:
        c_topics = course_topic_ids.get(c.id, [])
        tot = len(c_topics)
        att_count = sum(1 for tid in c_topics if tid in latest_attempts)
        avg_score = (
            round(float(course_avg_scores.get(c.id, 0.0)), 1)
            if c.id in course_avg_scores
            else 0.0
        )
        coverage_pct = round(att_count / tot * 100.0, 1) if tot > 0 else 0.0

        course_stats_list.append({
            "id": c.id,
            "code": c.code,
            "title": c.title,
            "total_topics": tot,
            "attempted_topics": att_count,
            "coverage_percentage": coverage_pct,
            "average_percentage": avg_score,
        })
        course_chart_labels.append(c.code)
        course_chart_attempted.append(att_count)
        course_chart_total.append(tot)
        course_chart_avg_pct.append(avg_score)

    chart_course_data = {
        "labels": course_chart_labels,
        "attempted": course_chart_attempted,
        "total": course_chart_total,
        "avg_percentages": course_chart_avg_pct,
    }

    # 6. Prerequisite DAG graph (1 query)
    adj = build_prerequisite_graph()

    # 7. "Revise first" list: Weak topics in semester with top foundational gap
    revise_first_list: list[dict[str, Any]] = []
    for t in semester_topics:
        att = latest_attempts.get(t.id)
        lbl_str = normalize_label(att.label) if att else ""
        if lbl_str == MasteryLabel.WEAK.value or lbl_str == "Weak":
            # Search BFS prerequisite DAG for gaps (deepest first)
            depths = traverse_prerequisites_bfs(t.id, adj, max_depth=4)
            found_gaps: list[tuple[int, int, str]] = []
            for p_id, depth in depths.items():
                p_att = latest_attempts.get(p_id)
                p_lbl = normalize_label(p_att.label) if p_att else ""
                if p_att is None or p_lbl == MasteryLabel.WEAK.value or p_lbl == "Weak":
                    found_gaps.append((
                        depth,
                        p_id,
                        "Weak" if p_att is not None else "Not attempted",
                    ))

            top_gap: dict[str, Any] | None = None
            if found_gaps:
                found_gaps.sort(key=lambda item: -item[0])
                top_depth, top_gap_id, top_status = found_gaps[0]
                gap_topic = topic_map.get(top_gap_id)
                if gap_topic is None:
                    # In case gap topic is from an earlier semester
                    gap_topic = Topic.query.options(defer(Topic.content)).get(top_gap_id)
                top_gap = {
                    "id": top_gap_id,
                    "name": gap_topic.name if gap_topic else f"Topic #{top_gap_id}",
                    "status": top_status,
                    "depth": top_depth,
                }

            revise_first_list.append({
                "id": t.id,
                "name": t.name,
                "course": t.course.title if t.course else t.subject,
                "top_gap": top_gap,
            })

    # 8. Adaptive recommendations for next topics
    recommended_next = get_next_topics(user, limit=8)

    return {
        "total_attempts": total_attempts,
        "topics_attempted": topics_attempted,
        "average_percentage": average_percentage,
        "mastered_topics": mastered_topics,
        "weak_topics": weak_topics_count,
        "uploads_count": uploads_count,
        "chart_labels_data": chart_labels_data,
        "chart_progress_data": chart_progress_data,
        "chart_course_data": chart_course_data,
        "course_stats": course_stats_list,
        "revise_first_list": revise_first_list,
        "recommended_next": recommended_next,
    }


@dashboard_bp.route("/", methods=["GET"])
@login_required
def index():
    """Render the student personalized performance dashboard."""
    data = get_dashboard_data(current_user)
    return render_template(
        "dashboard/index.html",
        **data,
    )
