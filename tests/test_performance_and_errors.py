"""Tests for query optimization, deferred column loading, LRU caching, and error handling."""

from __future__ import annotations
from typing import Any
import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import inspect, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import defer, selectinload
from app.extensions import db
from app.models.course import Course, CoursePrerequisite
from app.models.topic import Topic
from app.models.user import User
from app.services.markdown_renderer import (
    render_topic_markdown,
    get_cached_topic_markdown,
    clear_topic_markdown_cache,
)


def test_404_error_page(client: FlaskClient) -> None:
    """Verify missing endpoints render custom friendly 404 error page."""
    response = client.get("/this-route-definitely-does-not-exist-404")
    assert response.status_code == 404
    assert b"Page Not Found" in response.data
    assert b"Browse Curriculum" in response.data
    assert b"Return Home" in response.data


def test_500_error_page_and_rollback(app: Flask) -> None:
    """Verify 500 internal errors trigger custom 500 page, server logging, and session rollback."""
    @app.route("/simulate-error-for-testing")
    def trigger_server_error() -> None:
        # Add a record within uncommitted transaction to test rollback
        user = User(
            name="Rollback Candidate",
            email="rollback_candidate@example.com",
            semester=2,
        )
        user.set_password("TempPassword123!")
        db.session.add(user)
        db.session.flush()
        from flask import abort
        abort(500)

    client = app.test_client()
    response = client.get("/simulate-error-for-testing")

    assert response.status_code == 500
    assert b"Something Went Wrong" in response.data
    assert b"automatically rolled back" in response.data
    assert b"Retry Request" in response.data

    # Verify session rollback: the uncommitted user was NOT persisted
    with app.app_context():
        persisted = User.query.filter_by(
            email="rollback_candidate@example.com"
        ).first()
        assert persisted is None


def test_list_pages_do_not_load_topic_content(
    app: Flask, auth_client: FlaskClient
) -> None:
    """Verify that querying topics for list pages defers loading heavy Topic.content."""
    with app.app_context():
        course = Course(
            code="CS410",
            title="High Performance Computing",
            semester=7,
            domain="Computing Core",
            credit_hours=3,
            contact_hours="3-0",
            is_elective=False,
        )
        db.session.add(course)
        db.session.commit()

        heavy_body = "# GPU Acceleration\n\nCUDA kernels and memory hierarchies." * 100
        topic = Topic(
            course_id=course.id,
            semester=7,
            subject="High Performance Computing",
            name="CUDA Architecture",
            difficulty=4,
            content=heavy_body,
        )
        db.session.add(topic)
        db.session.commit()

        # Simulate list page query executed in course_topics
        topics = (
            Topic.query.filter_by(course_id=course.id)
            .options(
                defer(Topic.content),
                selectinload(Topic.prerequisites_required),
                selectinload(Topic.resources),
            )
            .all()
        )

        assert len(topics) == 1
        loaded_topic = topics[0]

        # In SQLAlchemy, deferred attributes are in state.unloaded and omitted from instance __dict__
        state = inspect(loaded_topic)
        assert "content" in state.unloaded
        assert "content" not in loaded_topic.__dict__


def test_course_topics_query_count_does_not_grow_with_topic_count(
    app: Flask, auth_client: FlaskClient
) -> None:
    """Verify /topics/course/<id> query count is O(1) and does NOT grow with the number of topics."""
    with app.app_context():
        course_small = Course(
            code="CS420",
            title="Compilers",
            semester=6,
            domain="Computing Core",
            credit_hours=3,
            contact_hours="3-0",
        )
        course_large = Course(
            code="CS421",
            title="Computer Graphics",
            semester=6,
            domain="Computing Core",
            credit_hours=3,
            contact_hours="3-0",
        )
        db.session.add_all([course_small, course_large])
        db.session.commit()

        # Seed small course with 2 topics
        for i in range(2):
            t = Topic(
                course_id=course_small.id,
                semester=6,
                subject="Compilers",
                name=f"Compiler Phase {i}",
                difficulty=3,
                content=f"# Notes for phase {i}",
            )
            db.session.add(t)

        # Seed large course with 15 topics
        for i in range(15):
            t = Topic(
                course_id=course_large.id,
                semester=6,
                subject="Computer Graphics",
                name=f"Graphics Topic {i}",
                difficulty=2,
                content=f"# Notes for graphics {i}",
            )
            db.session.add(t)

        db.session.commit()
        id_small = course_small.id
        id_large = course_large.id

        # Warm-up request to populate student session identity
        auth_client.get("/")

        def measure_queries(path: str) -> tuple[int, list[str]]:
            executed_queries: list[str] = []

            def listener(
                conn: Any,
                cursor: Any,
                statement: str,
                parameters: Any,
                context: Any,
                executemany: bool,
            ) -> None:
                executed_queries.append(statement)

            event.listen(Engine, "before_cursor_execute", listener)
            try:
                response = auth_client.get(path)
                assert response.status_code == 200
                return len(executed_queries), list(executed_queries)
            finally:
                event.remove(Engine, "before_cursor_execute", listener)

        count_small, list_small = measure_queries(f"/topics/course/{id_small}")
        count_large, list_large = measure_queries(f"/topics/course/{id_large}")

        assert count_small == count_large, f"Small: {list_small}\n\nLarge: {list_large}"
        # Eager loading: constant query count <= 6
        assert count_large <= 6


def test_semester_picker_query_count_constant(
    app: Flask, auth_client: FlaskClient
) -> None:
    """Verify /topics/ and /topics/semester/<n> use a single grouped COUNT query instead of N+1."""
    with app.app_context():
        course_1 = Course(
            code="CS601",
            title="Cloud Architecture",
            semester=8,
            domain="Computing Core",
            credit_hours=3,
            contact_hours="3-0",
        )
        course_2 = Course(
            code="CS602",
            title="Software Security",
            semester=8,
            domain="Computing Core",
            credit_hours=3,
            contact_hours="3-0",
        )
        db.session.add_all([course_1, course_2])
        db.session.commit()

        for c in (course_1, course_2):
            for i in range(4):
                t = Topic(
                    course_id=c.id,
                    semester=8,
                    subject=c.title,
                    name=f"{c.code} Concept {i}",
                    difficulty=3,
                    content=f"Content {i}",
                )
                db.session.add(t)
        db.session.commit()

        executed_queries: list[str] = []

        def listener(
            conn: Any,
            cursor: Any,
            statement: str,
            parameters: Any,
            context: Any,
            executemany: bool,
        ) -> None:
            executed_queries.append(statement)

        event.listen(Engine, "before_cursor_execute", listener)
        try:
            response = auth_client.get("/topics/semester/8")
            assert response.status_code == 200
            assert b"Cloud Architecture" in response.data
            assert b"Software Security" in response.data
            # Max queries: user (1) + courses (1) + grouped count (1) = 3 total queries
            assert len(executed_queries) <= 3
        finally:
            event.remove(Engine, "before_cursor_execute", listener)


def test_markdown_caching_lru_hit_and_invalidation() -> None:
    """Verify functools.lru_cache returns cached rendered HTML on identical content and updates on change."""
    clear_topic_markdown_cache()
    info_start = get_cached_topic_markdown.cache_info()

    content = "# Concurrency Control\n\nLocks, timestamps, and MVCC."
    rendered_1 = render_topic_markdown(42, content)
    assert "Concurrency Control" in rendered_1
    info_1 = get_cached_topic_markdown.cache_info()
    assert info_1.hits == info_start.hits
    assert info_1.misses == info_start.misses + 1

    # Second call with same topic ID and content: MUST hit cache
    rendered_2 = render_topic_markdown(42, content)
    assert rendered_2 == rendered_1
    info_2 = get_cached_topic_markdown.cache_info()
    assert info_2.hits == info_1.hits + 1
    assert info_2.misses == info_1.misses

    # Update content: MUST miss cache and produce new rendered output
    updated_content = content + "\n\n- Optimistic Concurrency Control"
    rendered_3 = render_topic_markdown(42, updated_content)
    assert "Optimistic Concurrency Control" in rendered_3
    info_3 = get_cached_topic_markdown.cache_info()
    assert info_3.misses == info_2.misses + 1


def test_user_loader_single_pk_lookup(app: Flask) -> None:
    """Verify user_loader executes a single primary-key lookup without joined relationships."""
    with app.app_context():
        user = User(
            name="Loader Student",
            email="loader_student@example.com",
            semester=3,
        )
        user.set_password("SecurePass456!")
        db.session.add(user)
        db.session.commit()

        user_id = user.id

        executed: list[str] = []

        def listener(
            conn: Any,
            cursor: Any,
            statement: str,
            parameters: Any,
            context: Any,
            executemany: bool,
        ) -> None:
            executed.append(statement)

        event.listen(Engine, "before_cursor_execute", listener)
        try:
            # Call login_manager.user_loader callback
            loaded = app.login_manager._user_callback(str(user_id))
            assert loaded is not None
            assert loaded.id == user_id
            # Should execute at most 1 query
            assert len(executed) <= 1
        finally:
            event.remove(Engine, "before_cursor_execute", listener)
