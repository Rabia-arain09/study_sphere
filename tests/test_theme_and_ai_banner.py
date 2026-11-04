"""Tests for theme modes and AI-notes banner functionality."""

from __future__ import annotations
import pytest
from flask import Flask
from flask.testing import FlaskClient
from app.extensions import db
from app.models.course import Course
from app.models.topic import Topic, ContentSource


@pytest.fixture
def theme_test_curriculum(app: Flask):
    """Seed test database with courses and topics for testing provenance and themes."""
    with app.app_context():
        course = Course(
            code="CS401",
            title="Software Architecture",
            semester=7,
            domain="Software Engineering",
            credit_hours=3,
            contact_hours="3-0",
            is_elective=False,
        )
        db.session.add(course)
        db.session.commit()

        # 1. Unreviewed AI-generated topic (Banner MUST appear, Card badge MUST NOT appear)
        t_ai_unreviewed = Topic(
            course_id=course.id,
            semester=7,
            subject="Software Architecture",
            name="Microservices Pattern",
            difficulty=3,
            week="1",
            content="# Microservices\n\nIndependent deployable services.",
            content_source=ContentSource.AI_GENERATED,
            content_reviewed=False,
        )
        # 2. Reviewed AI-generated topic (Banner MUST NOT appear)
        t_ai_reviewed = Topic(
            course_id=course.id,
            semester=7,
            subject="Software Architecture",
            name="Event-Driven Architecture",
            difficulty=4,
            week="2",
            content="# Event Driven\n\nAsynchronous message passing.",
            content_source=ContentSource.AI_GENERATED,
            content_reviewed=True,
        )
        # 3. Unreviewed lecture topic (Banner MUST NOT appear)
        t_lecture_unreviewed = Topic(
            course_id=course.id,
            semester=7,
            subject="Software Architecture",
            name="Monolithic Architecture",
            difficulty=2,
            week="3",
            content="# Monolith\n\nSingle unified codebase.",
            content_source=ContentSource.LECTURE,
            content_reviewed=False,
        )
        # 4. Reviewed lecture topic (Banner MUST NOT appear)
        t_lecture_reviewed = Topic(
            course_id=course.id,
            semester=7,
            subject="Software Architecture",
            name="Service-Oriented Architecture",
            difficulty=3,
            week="4",
            content="# SOA\n\nEnterprise service bus.",
            content_source=ContentSource.LECTURE,
            content_reviewed=True,
        )

        db.session.add_all([
            t_ai_unreviewed,
            t_ai_reviewed,
            t_lecture_unreviewed,
            t_lecture_reviewed,
        ])
        db.session.commit()

        return {
            "course_id": course.id,
            "ai_unreviewed_id": t_ai_unreviewed.id,
            "ai_reviewed_id": t_ai_reviewed.id,
            "lecture_unreviewed_id": t_lecture_unreviewed.id,
            "lecture_reviewed_id": t_lecture_reviewed.id,
        }


def test_navbar_theme_switch_unauthenticated_pages(client: FlaskClient):
    """Verify navbar theme switch is present on public pages including login and signup."""
    for path in ["/", "/auth/login", "/auth/signup"]:
        res = client.get(path)
        assert res.status_code == 200, f"Path {path} returned status {res.status_code}"
        assert b"theme-switch" in res.data, f"theme-switch missing from {path}"
        assert b'data-theme="light"' in res.data, f"Light theme button missing from {path}"
        assert b'data-theme="dark"' in res.data, f"Dark theme button missing from {path}"
        assert b'data-theme="highlight"' in res.data, f"Highlight theme button missing from {path}"
        # Anti-flash pre-paint script
        assert b"studysphere-theme" in res.data, f"Pre-paint anti-flash script missing from {path}"


def test_navbar_theme_switch_authenticated_pages(auth_client: FlaskClient, theme_test_curriculum):
    """Verify navbar theme switch is present on authenticated pages."""
    cid = theme_test_curriculum["course_id"]
    tid = theme_test_curriculum["ai_unreviewed_id"]
    for path in ["/dashboard/", "/upload/", "/quiz/history", f"/topics/course/{cid}", f"/topics/{tid}"]:
        res = auth_client.get(path)
        assert res.status_code == 200, f"Path {path} returned status {res.status_code}"
        assert b"theme-switch" in res.data, f"theme-switch missing from {path}"
        assert b'data-theme="light"' in res.data
        assert b'data-theme="dark"' in res.data
        assert b'data-theme="highlight"' in res.data


def test_banner_shows_only_for_unreviewed_ai_notes(auth_client: FlaskClient, theme_test_curriculum):
    """Verify the AI notes banner shows ONLY for topics where content_source is ai_generated and content_reviewed is false."""
    banner_text = b"AI-generated notes, not yet reviewed"

    # 1. AI + Unreviewed -> MUST show banner
    res_ai_unrev = auth_client.get(f"/topics/{theme_test_curriculum['ai_unreviewed_id']}")
    assert res_ai_unrev.status_code == 200
    assert banner_text in res_ai_unrev.data
    assert b"ai-notes-banner" in res_ai_unrev.data

    # 2. AI + Reviewed -> MUST NOT show banner
    res_ai_rev = auth_client.get(f"/topics/{theme_test_curriculum['ai_reviewed_id']}")
    assert res_ai_rev.status_code == 200
    assert banner_text not in res_ai_rev.data

    # 3. Lecture + Unreviewed -> MUST NOT show banner
    res_lec_unrev = auth_client.get(f"/topics/{theme_test_curriculum['lecture_unreviewed_id']}")
    assert res_lec_unrev.status_code == 200
    assert banner_text not in res_lec_unrev.data

    # 4. Lecture + Reviewed -> MUST NOT show banner
    res_lec_rev = auth_client.get(f"/topics/{theme_test_curriculum['lecture_reviewed_id']}")
    assert res_lec_rev.status_code == 200
    assert banner_text not in res_lec_rev.data


def test_cards_no_longer_show_badge(auth_client: FlaskClient, theme_test_curriculum):
    """Verify that topic cards on course listing page do NOT show the AI-generated badge."""
    course_id = theme_test_curriculum["course_id"]
    res = auth_client.get(f"/topics/course/{course_id}")
    assert res.status_code == 200

    # Ensure topic names are rendered
    assert b"Microservices Pattern" in res.data
    assert b"Event-Driven Architecture" in res.data
    assert b"Monolithic Architecture" in res.data
    assert b"Service-Oriented Architecture" in res.data

    # Verify no topic card shows "AI-generated" or "AI-generated, not yet reviewed" badge
    assert b"AI-generated, not yet reviewed" not in res.data
    assert b"AI-generated notes, not yet reviewed" not in res.data

    # Reviewed topics still show "Reviewed" badge
    assert b"Reviewed" in res.data


def test_dashboard_charts_theme_integration(auth_client: FlaskClient):
    """Verify dashboard contains Chart.js theme listeners and configuration."""
    res = auth_client.get("/dashboard/")
    assert res.status_code == 200
    assert b"getThemeChartColors" in res.data
    assert b"updateChartsTheme" in res.data
    assert b"themechanged" in res.data
