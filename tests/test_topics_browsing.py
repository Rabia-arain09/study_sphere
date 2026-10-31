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
    """Verify /topics/<id> renders sanitized markdown notes, links, and resources."""
    topic_id = seeded_curriculum["topic_1_id"]
    response = auth_client.get(f"/topics/{topic_id}")
    assert response.status_code == 200

    # Notes content rendered to HTML
    assert b"Processes and Threads" in response.data
    assert b"<strong>process</strong>" in response.data
    assert b"<li>State: Ready, Running, Blocked</li>" in response.data

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
    """Verify topic with empty content displays friendly message, not broken page."""
    topic_3_id = seeded_curriculum["topic_3_id"]
    response = auth_client.get(f"/topics/{topic_3_id}")
    assert response.status_code == 200
    assert b"No study notes available yet" in response.data


def test_topic_detail_not_found(auth_client: FlaskClient):
    """Verify non-existent topic returns HTTP 404."""
    assert auth_client.get("/topics/99999").status_code == 404
