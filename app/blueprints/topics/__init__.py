"""Topics blueprint for curriculum browsing (semester -> subject -> topic) and study notes."""

from __future__ import annotations
import re
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.orm import defer, joinedload, selectinload
from app.extensions import db
from app.models.course import Course, CoursePrerequisite
from app.models.prerequisite import Prerequisite
from app.models.topic import Topic
from app.services.markdown_renderer import render_topic_markdown

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

    return render_template(
        "topics/course.html",
        course=course,
        topics=ordered_topics,
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

    # Directed prerequisites: concepts required before taking this topic
    prerequisites = [
        prereq.prerequisite_topic
        for prereq in topic.prerequisites_required
        if prereq.prerequisite_topic is not None
    ]

    return render_template(
        "topics/topic.html",
        topic=topic,
        rendered_notes=rendered_notes,
        prerequisites=prerequisites,
        resources=topic.resources,
    )


# Alias endpoint for consistency
topics_bp.add_url_rule("/", endpoint="index", view_func=semester_picker)
