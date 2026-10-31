"""Topics blueprint for curriculum browsing (semester -> subject -> topic) and study notes."""

from __future__ import annotations
import re
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.course import Course
from app.models.topic import Topic
from app.services.markdown_renderer import render_markdown

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
    topic_count = Topic.query.filter_by(semester=default_semester).count()

    course_topic_counts = {
        course.id: len(course.topics) for course in courses
    }

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
    topic_count = Topic.query.filter_by(semester=semester).count()

    course_topic_counts = {
        course.id: len(course.topics) for course in courses
    }

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
    course = db.session.get(Course, course_id)
    if course is None:
        abort(404)
    topics = Topic.query.filter_by(course_id=course.id).all()
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
    topic = db.session.get(Topic, topic_id)
    if topic is None:
        abort(404)

    rendered_notes = render_markdown(topic.content) if topic.content else ""

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
