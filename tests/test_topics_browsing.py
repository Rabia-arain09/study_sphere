"""Unit tests for the curriculum and topics browsing blueprint."""

from __future__ import annotations
import pytest
from flask import Flask
from flask.testing import FlaskClient
from app.extensions import db
from app.models.course import Course
from app.models.topic import Topic, ContentSource
from app.models.prerequisite import Prerequisite
from app.models.resource import Resource, ResourceType
from app.models.user import User


@pytest.fixture
def seeded_curriculum(app: Flask):
    """Seed test database with courses, topics, prerequisites, and resources."""
    with app.app_context():
        # Semester 5 course with topics
        c5 = Course(
            code="CS301",
            title="Operating Systems",
            semester=5,
            domain="Computing Core",
            credit_hours=3,
            contact_hours="3-0",
            is_elective=False,
        )
        # Semester 1 course with NO topics (for coming-soon testing)
        c1 = Course(
            code="CS101",
            title="Introduction to Programming",
            semester=1,
            domain="Computing Core",
            credit_hours=3,
            contact_hours="3-3",
            is_elective=False,
        )
        db.session.add_all([c5, c1])
        db.session.commit()

        # Topics for CS301 (ordered by week, with review status variations)
        t1 = Topic(
            course_id=c5.id,
            semester=5,
            subject="Operating Systems",
            name="Processes and Threads",
            difficulty=2,
            week="1",
            description="Introduction to processes and concurrency.",
            content="# Processes and Threads\n\nA **process** is an executing program instance.\n\n- State: Ready, Running, Blocked",
            content_source=ContentSource.AI_GENERATED,
            content_reviewed=False,  # Unreviewed -> badge must appear
        )
        t2 = Topic(
            course_id=c5.id,
            semester=5,
            subject="Operating Systems",
            name="CPU Scheduling Algorithms",
            difficulty=3,
            week="2",
            description="First-Come First-Served, Round Robin, Multi-level queues.",
            content="## CPU Scheduling\n\nOptimal scheduling maximizes CPU utilization.",
            content_source=ContentSource.LECTURE,
            content_reviewed=True,  # Reviewed -> verified badge
        )
        t3 = Topic(
            course_id=c5.id,
            semester=5,
            subject="Operating Systems",
            name="Virtual Memory and Paging",
            difficulty=4,
            week="3",
            description="Page replacement and translation lookaside buffer.",
            content=None,  # Empty content -> friendly empty notes message
            content_source=ContentSource.AI_GENERATED,
            content_reviewed=False,
        )
        db.session.add_all([t1, t2, t3])
        db.session.commit()

        # Prerequisite: Topic 2 requires Topic 1
        prereq = Prerequisite(topic_id=t2.id, prerequisite_topic_id=t1.id)
        db.session.add(prereq)

        # Resource on Topic 1
        res = Resource(
            topic_id=t1.id,
            title="Process Lifecycle Diagram",
            type=ResourceType.DIAGRAM,
            url="https://example.com/process-lifecycle.png",
        )
        db.session.add(res)
        db.session.commit()

        return {
            "course_sem5_id": c5.id,
            "course_sem1_id": c1.id,
            "topic_1_id": t1.id,
            "topic_2_id": t2.id,
            "topic_3_id": t3.id,
        }


def test_topics_index_login_required(client: FlaskClient):
    """Verify /topics/ requires authentication."""
    response = client.get("/topics/")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_topics_index_default_semester(auth_client: FlaskClient, seeded_curriculum):
    """Verify /topics/ renders 200 and defaults to user's semester (Semester 5)."""
    response = auth_client.get("/topics/")
    assert response.status_code == 200
    assert b"Curriculum Subjects" in response.data
    # Check semester pills 1-8 are rendered
    for sem in range(1, 9):
        assert f"Semester {sem}".encode() in response.data
    # Active semester is Semester 5
    assert b"Semester 5 Subjects" in response.data
    assert b"Operating Systems" in response.data
    assert b"CS301" in response.data


def test_semester_view_with_topics(auth_client: FlaskClient, seeded_curriculum):
    """Verify /topics/semester/5 lists subjects and active topics."""
    response = auth_client.get("/topics/semester/5")
    assert response.status_code == 200
    assert b"Semester 5 Subjects" in response.data
    assert b"Operating Systems" in response.data
    assert b"CS301" in response.data


def test_semester_view_no_topics_coming_soon(auth_client: FlaskClient, seeded_curriculum):
    """Verify semester with 0 topics renders friendly coming soon message, not an error."""
    # Semester 1 has course CS101 but 0 topics
    response = auth_client.get("/topics/semester/1")
    assert response.status_code == 200
    assert b"Notes coming soon" in response.data
    assert b"Introduction to Programming" in response.data
    # Semester 2 has 0 courses and 0 topics
    response_sem2 = auth_client.get("/topics/semester/2")
    assert response_sem2.status_code == 200
    assert b"Notes coming soon" in response_sem2.data


def test_semester_view_invalid_semester_404(auth_client: FlaskClient):
    """Verify out-of-range semesters return HTTP 404."""
    assert auth_client.get("/topics/semester/0").status_code == 404
    assert auth_client.get("/topics/semester/9").status_code == 404
    assert auth_client.get("/topics/semester/99").status_code == 404


def test_course_topics_view(auth_client: FlaskClient, seeded_curriculum):
    """Verify /topics/course/<id> lists topics ordered by week, difficulty, and review badge."""
    course_id = seeded_curriculum["course_sem5_id"]
    response = auth_client.get(f"/topics/course/{course_id}")
    assert response.status_code == 200
    assert b"Operating Systems" in response.data
    assert b"CS301" in response.data

    # Check topic names
    assert b"Processes and Threads" in response.data
    assert b"CPU Scheduling Algorithms" in response.data
    assert b"Virtual Memory and Paging" in response.data

    # Check week ordering
    pos1 = response.data.find(b"Processes and Threads")
    pos2 = response.data.find(b"CPU Scheduling Algorithms")
    pos3 = response.data.find(b"Virtual Memory and Paging")
    assert pos1 < pos2 < pos3

    # Check difficulty indicators
    assert b"Level 2/5" in response.data
    assert b"Level 3/5" in response.data
    assert b"Level 4/5" in response.data

    # Check unreviewed badge: "AI-generated, not yet reviewed"
    assert b"AI-generated, not yet reviewed" in response.data
    assert b"Reviewed" in response.data

    # Check week headings (Requirement 2)
    assert b"Week 1" in response.data
    assert b"Week 2" in response.data
    assert b"Week 3" in response.data


def test_course_topics_week_grouping_and_other_group(
    app: Flask, auth_client: FlaskClient
) -> None:
    """Verify course page groups topics under week headings and places unassigned topics in 'Other'."""
    with app.app_context():
        course = Course(
            code="CS350",
            title="Machine Learning",
            semester=5,
            domain="Computing Core",
            credit_hours=3,
            contact_hours="3-0",
            is_elective=False,
        )
        db.session.add(course)
        db.session.commit()

        # Create topics with week ranges, single weeks, and no week
        t1 = Topic(
            course_id=course.id,
            semester=5,
            subject="Machine Learning",
            name="Introduction to ML",
            difficulty=1,
            week="1",
            content_reviewed=True,
        )
        t2 = Topic(
            course_id=course.id,
            semester=5,
            subject="Machine Learning",
            name="Regression Models",
            difficulty=2,
            week="2-3",
            content_reviewed=False,
        )
        t3 = Topic(
            course_id=course.id,
            semester=5,
            subject="Machine Learning",
            name="Neural Networks",
            difficulty=4,
            week="4-5",
            content_reviewed=True,
        )
        t_unassigned = Topic(
            course_id=course.id,
            semester=5,
            subject="Machine Learning",
            name="Capstone Project Overview",
            difficulty=3,
            week=None,
            content_reviewed=False,
        )
        db.session.add_all([t1, t2, t3, t_unassigned])
        db.session.commit()
        cid = course.id

    response = auth_client.get(f"/topics/course/{cid}")
    assert response.status_code == 200

    # Verify week headings are present
    assert b"Week 1" in response.data
    assert b"Week 2-3" in response.data
    assert b"Week 4-5" in response.data
    assert b"Other" in response.data

    # Verify chronological ordering and 'Other' group placed at the end
    pos_w1 = response.data.find(b"Week 1")
    pos_w23 = response.data.find(b"Week 2-3")
    pos_w45 = response.data.find(b"Week 4-5")
    pos_other = response.data.find(b"Other")
    assert pos_w1 < pos_w23 < pos_w45 < pos_other

    # Verify topic placement
    pos_t1 = response.data.find(b"Introduction to ML")
    pos_t2 = response.data.find(b"Regression Models")
    pos_t3 = response.data.find(b"Neural Networks")
    pos_t_unassigned = response.data.find(b"Capstone Project Overview")
    assert pos_w1 < pos_t1 < pos_w23 < pos_t2 < pos_w45 < pos_t3 < pos_other < pos_t_unassigned

    # Verify difficulty and review badges are retained
    assert b"Level 1/5" in response.data
    assert b"Level 2/5" in response.data
    assert b"Level 4/5" in response.data
    assert b"Level 3/5" in response.data
    assert b"AI-generated, not yet reviewed" in response.data
    assert b"Reviewed" in response.data


def test_topic_detail_back_button_and_breadcrumb_course_name(
    auth_client: FlaskClient, seeded_curriculum
) -> None:
    """Verify /topics/<id> back button and breadcrumb show course name instead of course code."""
    topic_id = seeded_curriculum["topic_1_id"]
    response = auth_client.get(f"/topics/{topic_id}")
    assert response.status_code == 200

    # Back button text: "← Back to <course name> topics"
    assert "← Back to Operating Systems topics".encode("utf-8") in response.data
    assert b"Back to CS301 Topics" not in response.data

    # Breadcrumb trail contains course title
    assert b">Operating Systems</a>" in response.data
    # Header badge contains course title
    assert b">Operating Systems</span>" in response.data
    # Course code CS301 must NOT be shown where course name should be
    assert b">CS301</a>" not in response.data
    assert b">CS301: Operating Systems</span>" not in response.data


def test_format_week_heading_and_grouping() -> None:
    """Verify week formatting and grouping utility functions with varied inputs."""
    from app.blueprints.topics import format_week_heading, group_topics_by_week

    assert format_week_heading("1") == "Week 1"
    assert format_week_heading("Week 1") == "Week 1"
    assert format_week_heading("2-3") == "Week 2-3"
    assert format_week_heading("Week 4-5") == "Week 4-5"
    assert format_week_heading(None) == "Other"
    assert format_week_heading("") == "Other"
    assert format_week_heading("   ") == "Other"
    assert format_week_heading("Orientation") == "Other"


def test_course_topics_empty_coming_soon(auth_client: FlaskClient, seeded_curriculum):
    """Verify course with 0 topics displays friendly notes coming soon message."""
    course_id = seeded_curriculum["course_sem1_id"]
    response = auth_client.get(f"/topics/course/{course_id}")
    assert response.status_code == 200
    assert b"Notes coming soon" in response.data
    assert b"Introduction to Programming" in response.data


def test_course_topics_not_found(auth_client: FlaskClient):
    """Verify non-existent course returns HTTP 404."""
    assert auth_client.get("/topics/course/99999").status_code == 404


def test_topic_detail_notes_reader(auth_client: FlaskClient, seeded_curriculum):
    """Verify /topics/<id> renders sanitized markdown notes, links, reading time, and resources."""
    topic_id = seeded_curriculum["topic_1_id"]
    response = auth_client.get(f"/topics/{topic_id}")
    assert response.status_code == 200

    # Notes content rendered to HTML
    assert b"Processes and Threads" in response.data
    assert b"<strong>process</strong>" in response.data
    assert b"<li>State: Ready, Running, Blocked</li>" in response.data

    # Reading time appears on Study Notes header, old label is removed
    assert b"Pedagogical Ground Truth" not in response.data
    assert b"1 min read" in response.data

    # Attached resource displayed
    assert b"Process Lifecycle Diagram" in response.data
    assert b"https://example.com/process-lifecycle.png" in response.data

    # Provenance badge
    assert b"AI-generated, not yet reviewed" in response.data


def test_topic_detail_prerequisites_as_links(auth_client: FlaskClient, seeded_curriculum):
    """Verify topic page lists prerequisite concepts as clickable links."""
    # Topic 2 requires Topic 1
    topic_2_id = seeded_curriculum["topic_2_id"]
    topic_1_id = seeded_curriculum["topic_1_id"]
    response = auth_client.get(f"/topics/{topic_2_id}")
    assert response.status_code == 200

    # Prerequisite link to topic 1
    assert f'href="/topics/{topic_1_id}"'.encode() in response.data
    assert b"Processes and Threads" in response.data


def test_topic_detail_empty_notes_friendly_message(auth_client: FlaskClient, seeded_curriculum):
    """Verify topic with empty content displays friendly message and no reading time."""
    topic_3_id = seeded_curriculum["topic_3_id"]
    response = auth_client.get(f"/topics/{topic_3_id}")
    assert response.status_code == 200
    assert b"No study notes available yet" in response.data
    assert b"min read" not in response.data
    assert b"Pedagogical Ground Truth" not in response.data


def test_topic_detail_not_found(auth_client: FlaskClient):
    """Verify non-existent topic returns HTTP 404."""
    assert auth_client.get("/topics/99999").status_code == 404


def test_topic_detail_reading_time_and_minimum(
    auth_client: FlaskClient, app: Flask, seeded_curriculum
):
    """Verify reading time calculation on topic detail view, including 1 min minimum and ~200 wpm scaling."""
    with app.app_context():
        course_id = seeded_curriculum["course_sem5_id"]
        # Topic with 1200 words (~6 min read)
        t_long = Topic(
            course_id=course_id,
            semester=5,
            subject="Operating Systems",
            name="Advanced Kernel Architecture",
            difficulty=4,
            content="kernel " * 1200,
        )
        # Topic with short text (15 words -> minimum 1 min read)
        t_short = Topic(
            course_id=course_id,
            semester=5,
            subject="Operating Systems",
            name="Microkernels and Monolithic Kernels",
            difficulty=3,
            content="Microkernels isolate services in user space while monolithic kernels run everything inside supervisor mode.",
        )
        db.session.add_all([t_long, t_short])
        db.session.commit()
        long_id = t_long.id
        short_id = t_short.id

    # Verify 1200 words renders "6 min read" and excludes old badge
    resp_long = auth_client.get(f"/topics/{long_id}")
    assert resp_long.status_code == 200
    assert b"6 min read" in resp_long.data
    assert b"Pedagogical Ground Truth" not in resp_long.data

    # Verify short content renders "1 min read" (minimum 1 minute) and excludes old badge
    resp_short = auth_client.get(f"/topics/{short_id}")
    assert resp_short.status_code == 200
    assert b"1 min read" in resp_short.data
    assert b"Pedagogical Ground Truth" not in resp_short.data

