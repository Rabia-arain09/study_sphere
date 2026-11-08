"""Tests for verified topic resource loading and display."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from flask.testing import FlaskClient

from app.extensions import db
from app.models.attempt import Attempt
from app.models.course import Course
from app.models.resource import Resource, ResourceType
from app.models.topic import Topic
from app.models.user import User
from app.services.resource_loader import (
    ResourceLoader,
    ResourceValidationError,
)


def _create_topic(semester: int = 5) -> Topic:
    """Create one topic for resource loader and page tests."""
    course = Course(
        code=f"RESOURCE{semester}",
        title=f"Resource Testing {semester}",
        semester=semester,
        domain="Computer Science",
        credit_hours=3,
        contact_hours="3-0-3",
    )
    db.session.add(course)
    db.session.flush()
    topic = Topic(
        course_id=course.id,
        semester=semester,
        subject=course.title,
        name="Resource topic",
        difficulty=1,
        content="A short note for further reading tests.",
    )
    db.session.add(topic)
    db.session.flush()
    return topic


def _write_resources(path: Path, rows: list[list[str]]) -> None:
    """Write a resource CSV using the production schema."""
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["subject", "topic", "title", "type", "url"])
        writer.writerows(rows)


def test_resource_loader_is_idempotent_and_preserves_users_and_attempts(
    app,
    test_user: User,
    tmp_path: Path,
) -> None:
    """Load each link once without changing records outside resources."""
    with app.app_context():
        topic = _create_topic()
        db.session.add(
            Attempt(
                user_id=test_user.id,
                topic_id=topic.id,
                score=1,
                total_questions=1,
                wrong_count=0,
                attempt_number=1,
            )
        )
        db.session.commit()
        _write_resources(
            tmp_path / "resources.csv",
            [
                [
                    topic.subject,
                    topic.name,
                    "Reference guide",
                    "link",
                    "https://example.org/reference",
                ]
            ],
        )
        user_count = User.query.count()
        attempt_count = Attempt.query.count()

        first = ResourceLoader(tmp_path).load()
        second = ResourceLoader(tmp_path).load()

        assert first.links_added == 1
        assert second.links_added == 0
        assert second.links_unchanged == 1
        assert Resource.query.filter_by(topic_id=topic.id).count() == 1
        assert User.query.count() == user_count
        assert Attempt.query.count() == attempt_count


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "ftp://example.org/resource",
        "https:///missing-host",
        "/relative/path",
    ],
)
def test_resource_loader_rejects_non_http_or_invalid_urls(
    app,
    tmp_path: Path,
    url: str,
) -> None:
    """Accept only fully qualified HTTP and HTTPS links."""
    with app.app_context():
        topic = _create_topic()
        db.session.commit()
        _write_resources(
            tmp_path / "resources.csv",
            [[topic.subject, topic.name, "Invalid reference", "link", url]],
        )

        with pytest.raises(ResourceValidationError, match="HTTP or HTTPS"):
            ResourceLoader(tmp_path).load()

        assert Resource.query.count() == 0


@pytest.mark.parametrize("scheme", ["http", "https"])
def test_resource_loader_accepts_http_and_https_urls(
    app,
    tmp_path: Path,
    scheme: str,
) -> None:
    """Accept fully qualified HTTP and HTTPS reference URLs."""
    with app.app_context():
        topic = _create_topic()
        db.session.commit()
        _write_resources(
            tmp_path / "resources.csv",
            [
                [
                    topic.subject,
                    topic.name,
                    "Valid reference",
                    "link",
                    f"{scheme}://example.org/reference",
                ]
            ],
        )

        summary = ResourceLoader(tmp_path).load()

        assert summary.links_added == 1
        assert Resource.query.filter_by(topic_id=topic.id).count() == 1


def test_resource_loader_does_not_import_other_semesters(
    app,
    tmp_path: Path,
) -> None:
    """Reject an out-of-scope topic rather than adding a resource to it."""
    with app.app_context():
        topic = _create_topic(semester=6)
        db.session.commit()
        _write_resources(
            tmp_path / "resources.csv",
            [
                [
                    topic.subject,
                    topic.name,
                    "Out of scope",
                    "link",
                    "https://example.org/reference",
                ]
            ],
        )

        with pytest.raises(ResourceValidationError, match="Semester 5 topic"):
            ResourceLoader(tmp_path).load()

        assert Resource.query.count() == 0


def test_topic_page_shows_further_reading_with_safe_external_links(
    app,
    auth_client: FlaskClient,
) -> None:
    """Render reference links at the end of the topic notes with safe attributes."""
    with app.app_context():
        topic = _create_topic()
        db.session.add(
            Resource(
                topic_id=topic.id,
                title="Official reference",
                type=ResourceType.LINK,
                url="https://docs.example.org/reference",
            )
        )
        db.session.commit()
        topic_id = topic.id

    response = auth_client.get(f"/topics/{topic_id}")

    assert response.status_code == 200
    assert b"Further reading" in response.data
    assert b"Official reference" in response.data
    assert b"docs.example.org" in response.data
    assert (
        b'href="https://docs.example.org/reference" target="_blank" '
        b'rel="noopener noreferrer"' in response.data
    )
    assert response.data.index(b"Further reading") > response.data.index(
        b"A short note for further reading tests."
    )


def test_topic_page_hides_further_reading_when_no_links(
    app,
    auth_client: FlaskClient,
) -> None:
    """Omit the Further reading section when a topic has no link resources."""
    with app.app_context():
        topic = _create_topic()
        db.session.commit()
        topic_id = topic.id

    response = auth_client.get(f"/topics/{topic_id}")

    assert response.status_code == 200
    assert b"Further reading" not in response.data
