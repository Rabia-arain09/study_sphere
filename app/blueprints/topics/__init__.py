"""Topics blueprint for curriculum browsing (semester -> subject -> topic) and study notes."""

from __future__ import annotations
import re
from typing import Any
from flask import Blueprint, render_template, abort, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.orm import defer, joinedload, selectinload
from app.extensions import db
from app.models.course import Course, CoursePrerequisite
from app.models.prerequisite import Prerequisite
from app.models.topic import Topic
from app.models.attempt import Attempt
from app.services.markdown_renderer import (
    calculate_reading_time,
    render_topic_markdown,
)
from app.services.recommendation_service import (
    get_recommendations,
    get_related_topics,
)

topics_bp: Blueprint = Blueprint("topics", __name__)


def week_sort_key(topic: Topic) -> tuple[int, int, str]:
    """Generate a sorting tuple for ordering topics by academic week.

    Parses week indicators (e.g., '1', '2-3', '10', 'Week 4') into integer ranges,
    placing unassigned topics deterministically at the end.

    Args:
        topic: Topic instance to extract week sort key from.

    Returns:
        tuple[int, int, str]: Sort tuple (start_week, end_week, topic_name).
    """
    if not topic.week:
        return (999, 999, topic.name.lower())
    numbers = [int(n) for n in re.findall(r"\d+", str(topic.week))]
    if numbers:
        start = numbers[0]
        end = numbers[-1] if len(numbers) > 1 else start
        return (start, end, topic.name.lower())
    return (998, 998, topic.name.lower())


def format_week_heading(week: str | None) -> str:
    """Format a topic's week indicator into a canonical group heading.

    Examples:
        '1' -> 'Week 1'
        'Week 1' -> 'Week 1'
        '2-3' -> 'Week 2-3'
        'Week 4-5' -> 'Week 4-5'
        None / '' / 'Unassigned' -> 'Other'

    Args:
        week: Raw week indicator string from topic model or None.

    Returns:
        str: Group heading string ('Week X', 'Week X-Y', or 'Other').
    """
    if not week:
        return "Other"
    clean = str(week).strip()
    if not clean:
        return "Other"
    # Find all numeric sequences in the week value
    numbers = re.findall(r"\d+", clean)
    if not numbers:
        return "Other"
    if clean.lower().startswith("week"):
        clean = clean[4:].strip()
    return f"Week {clean}"


def group_topics_by_week(topics: list[Topic]) -> list[dict[str, Any]]:
    """Group topics under week headings preserving chronological academic week order.

    Topics are sorted using existing `week_sort_key` logic. Chronologically valid
    week indicators are partitioned into groups labeled 'Week 1', 'Week 2-3', etc.,
    while topics without a valid week indicator are gathered into an 'Other' group
    positioned deterministically at the end.

    Args:
        topics: Collection of Topic instances for a course.

    Returns:
        list[dict[str, Any]]: Ordered list of group dictionaries containing:
            - 'heading': Display title for the week group (e.g., 'Week 1', 'Other').
            - 'topics': List of Topic objects belonging to this week group.
    """
    ordered_topics = sorted(topics, key=week_sort_key)
    groups: dict[str, list[Topic]] = {}
    other_topics: list[Topic] = []

    for topic in ordered_topics:
        heading = format_week_heading(topic.week)
        if heading == "Other":
            other_topics.append(topic)
        else:
            if heading not in groups:
                groups[heading] = []
            groups[heading].append(topic)

    result: list[dict[str, Any]] = [
        {"heading": heading, "topics": group_topics}
        for heading, group_topics in groups.items()
    ]
    if other_topics:
        result.append({"heading": "Other", "topics": other_topics})

    return result


@topics_bp.route("/", methods=["GET"])
@login_required
def semester_picker():
    """Display the academic semester picker (1-8), defaulting to user's enrolled semester."""
    user_semester = current_user.semester if current_user.is_authenticated else 1
    # Constrain fallback to 1-8
    default_semester = user_semester if 1 <= user_semester <= 8 else 1

    semesters = list(range(1, 9))
    courses = Course.query.filter_by(semester=default_semester).order_by(Course.code).all()

    # Efficient grouped COUNT query: 1 query for all courses in this semester
    # Replaces N+1 queries from iterating course.topics
    topic_counts = dict(
        db.session.query(Topic.course_id, func.count(Topic.id))
        .filter(Topic.semester == default_semester)
        .group_by(Topic.course_id)
        .all()
    )
    course_topic_counts = {course.id: topic_counts.get(course.id, 0) for course in courses}
    topic_count = sum(course_topic_counts.values())

    return render_template(
        "topics/index.html",
        semesters=semesters,
        selected_semester=default_semester,
        courses=courses,
        topic_count=topic_count,
        course_topic_counts=course_topic_counts,
    )


@topics_bp.route("/semester/<int:semester>", methods=["GET"])
@login_required
def semester_view(semester: int):
    """List academic subjects (courses) belonging to a specific semester."""
    if semester < 1 or semester > 8:
        abort(404)

    semesters = list(range(1, 9))
    courses = Course.query.filter_by(semester=semester).order_by(Course.code).all()

    # Efficient grouped COUNT query: 1 query for all courses in this semester
    topic_counts = dict(
        db.session.query(Topic.course_id, func.count(Topic.id))
        .filter(Topic.semester == semester)
        .group_by(Topic.course_id)
        .all()
    )
    course_topic_counts = {course.id: topic_counts.get(course.id, 0) for course in courses}
    topic_count = sum(course_topic_counts.values())

    return render_template(
        "topics/semester.html",
        semesters=semesters,
        semester=semester,
        courses=courses,
        topic_count=topic_count,
        course_topic_counts=course_topic_counts,
    )


@topics_bp.route("/course/<int:course_id>", methods=["GET"])
@login_required
def course_topics(course_id: int):
    """List topics of a subject/course ordered by week, with difficulty and review badges."""
    course = (
        Course.query.filter_by(id=course_id)
        .options(
            selectinload(Course.prerequisites_required).joinedload(
                CoursePrerequisite.prerequisite_course
            )
        )
        .first()
    )
    if course is None:
        abort(404)

    # Defer heavy Topic.content on list page and eager-load prerequisite/resource counts
    topics = (
        Topic.query.filter_by(course_id=course.id)
        .options(
            defer(Topic.content),
            selectinload(Topic.prerequisites_required),
            selectinload(Topic.resources),
        )
        .all()
    )
    ordered_topics = sorted(topics, key=week_sort_key)
    grouped_topics = group_topics_by_week(ordered_topics)

    return render_template(
        "topics/course.html",
        course=course,
        topics=ordered_topics,
        grouped_topics=grouped_topics,
    )


@topics_bp.route("/<int:topic_id>", methods=["GET"])
@login_required
def topic_detail(topic_id: int):
    """Render topic study notes reader, prerequisites as links, and attached resources."""
    topic = (
        Topic.query.filter_by(id=topic_id)
        .options(
            joinedload(Topic.course),
            selectinload(Topic.prerequisites_required).joinedload(
                Prerequisite.prerequisite_topic
            ),
            selectinload(Topic.resources),
        )
        .first()
    )
    if topic is None:
        abort(404)

    rendered_notes = (
        render_topic_markdown(topic.id, topic.content) if topic.content else ""
    )
    reading_time = calculate_reading_time(topic.content)

    # Directed prerequisites: concepts required before taking this topic
    prerequisites = [
        prereq.prerequisite_topic
        for prereq in topic.prerequisites_required
        if prereq.prerequisite_topic is not None
    ]

    related_topics = get_related_topics(topic.id, k=5)

    # Fetch user's quiz attempt history for this topic in a single indexed query (no N+1)
    user_attempts = (
        Attempt.query.filter_by(user_id=current_user.id, topic_id=topic.id)
        .order_by(Attempt.created_at.desc(), Attempt.id.desc())
        .all()
    )
    last_attempt = user_attempts[0] if user_attempts else None
    attempt_count = len(user_attempts)

    return render_template(
        "topics/topic.html",
        topic=topic,
        rendered_notes=rendered_notes,
        prerequisites=prerequisites,
        resources=topic.resources,
        related_topics=related_topics,
        reading_time=reading_time,
        last_attempt=last_attempt,
        attempt_count=attempt_count,
    )


@topics_bp.route("/<int:topic_id>/related", methods=["GET"])
@login_required
def related_topics(topic_id: int):
    """Return JSON list of top-5 related topics for a given topic.

    Uses a single database query to fetch target topic existence and all
    recommended topic entities with eager-loaded course relationships.
    """
    recs = get_recommendations(topic_id=topic_id, k=5)
    rec_ids = [item[0] for item in recs]

    # Fetch target topic and all recommendation candidates in a single SQL query
    all_needed_ids = [topic_id] + rec_ids
    topics = (
        Topic.query.options(joinedload(Topic.course))
        .filter(Topic.id.in_(all_needed_ids))
        .all()
    )
    topic_map = {t.id: t for t in topics}

    if topic_id not in topic_map:
        abort(404)

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

    return jsonify(results)


# Alias endpoint for consistency
topics_bp.add_url_rule("/", endpoint="index", view_func=semester_picker)
