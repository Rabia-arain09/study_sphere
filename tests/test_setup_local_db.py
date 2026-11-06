"""Unit and integration tests for the setup-local-db CLI command."""

from __future__ import annotations
import csv
from pathlib import Path
from flask import Flask
from app import create_app
from app.extensions import db
from app.models import Course, CoursePrerequisite, Topic, Prerequisite


def _data_counts() -> tuple[int, int, int]:
    """Return current topic, prerequisite, and note-file counts."""
    with Path("data/topics.csv").open(encoding="utf-8-sig", newline="") as file:
        topic_count = sum(1 for _ in csv.DictReader(file))
    with Path("data/topic_prerequisites.csv").open(
        encoding="utf-8-sig", newline=""
    ) as file:
        prerequisite_count = sum(1 for _ in csv.DictReader(file))
    note_count = sum(1 for _ in Path("data/notes").rglob("*.md"))
    return topic_count, prerequisite_count, note_count


def _create_sqlite_test_app(db_path: Path) -> Flask:
    """Create a Flask test application configured for a specific SQLite file."""
    app = create_app("testing")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path.as_posix()}"
    app.config["TESTING"] = True
    return app


def test_setup_local_db_runs_on_sqlite(tmp_path: Path) -> None:
    """Verify setup-local-db command initializes schema, curriculum, and notes on SQLite."""
    db_file = tmp_path / "studysphere_test.db"
    app = _create_sqlite_test_app(db_file)
    runner = app.test_cli_runner()
    topic_count, prerequisite_count, note_count = _data_counts()

    result = runner.invoke(args=["setup-local-db"])

    assert result.exit_code == 0
    assert "StudySphere Local SQLite Database Setup" in result.output
    assert "[1/3] Preparing database schema..." in result.output
    assert f"Processed 44 courses, {topic_count} topics" in result.output
    assert f"Processed {note_count} note files ({note_count} updated" in result.output
    assert "Local SQLite database setup completed successfully!" in result.output
    assert "> Total Courses : 44" in result.output
    assert f"> Total Topics  : {topic_count}" in result.output
    assert f"> Total Notes   : {note_count}" in result.output

    # Verify persistent database state within application context
    with app.app_context():
        assert Course.query.count() == 44
        assert Topic.query.count() == topic_count
        assert (
            Topic.query.filter(Topic.content.isnot(None), Topic.content != "").count()
            == topic_count
        )
        assert CoursePrerequisite.query.count() == 12
        assert Prerequisite.query.count() == prerequisite_count

        # Sample course and topic verification
        ml_course = Course.query.filter_by(title="Machine Learning").first()
        assert ml_course is not None
        assert ml_course.semester == 5

        ml_topic = Topic.query.filter_by(name="Introduction to Machine Learning").first()
        assert ml_topic is not None
        assert ml_topic.content is not None
        assert len(ml_topic.content) > 50


def test_setup_local_db_is_idempotent(tmp_path: Path) -> None:
    """Verify setup-local-db is strictly idempotent and safe to execute repeatedly."""
    db_file = tmp_path / "studysphere_idempotent.db"
    app = _create_sqlite_test_app(db_file)
    runner = app.test_cli_runner()
    topic_count, _, note_count = _data_counts()

    # First execution - initial ingestion
    res1 = runner.invoke(args=["setup-local-db"])
    assert res1.exit_code == 0
    assert f"Processed {note_count} note files ({note_count} updated" in res1.output

    # Second execution - idempotent pass
    res2 = runner.invoke(args=["setup-local-db"])
    assert res2.exit_code == 0
    assert (
        f"Processed {note_count} note files (0 updated, {note_count} unchanged, 0 skipped)"
        in res2.output
    )
    assert "> Total Courses : 44" in res2.output
    assert f"> Total Topics  : {topic_count}" in res2.output
    assert f"> Total Notes   : {note_count}" in res2.output

    with app.app_context():
        assert Course.query.count() == 44
        assert Topic.query.count() == topic_count
        assert (
            Topic.query.filter(Topic.content.isnot(None), Topic.content != "").count()
            == topic_count
        )


def test_setup_local_db_refuses_postgresql_url() -> None:
    """Verify setup-local-db refuses to execute when configured against PostgreSQL."""
    app = create_app("testing")
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "postgresql+psycopg2://postgres:secretPass@localhost:5432/studysphere_db"
    )
    runner = app.test_cli_runner()

    result = runner.invoke(args=["setup-local-db"])

    assert result.exit_code != 0
    assert "Error: setup-local-db is restricted to local SQLite databases." in result.output
    assert "Refusing to run against PostgreSQL database." in result.output


def test_setup_local_db_refuses_postgres_legacy_scheme() -> None:
    """Verify setup-local-db refuses to execute when URI uses legacy postgres:// prefix."""
    app = create_app("testing")
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "postgres://postgres:secretPass@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
    )
    runner = app.test_cli_runner()

    result = runner.invoke(args=["setup-local-db"])

    assert result.exit_code != 0
    assert "Refusing to run against PostgreSQL database." in result.output


def test_setup_local_db_refuses_non_sqlite_dialect() -> None:
    """Verify setup-local-db refuses non-SQLite dialects with masked diagnostic message."""
    app = create_app("testing")
    app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://user:secret@localhost:3306/db"
    runner = app.test_cli_runner()

    result = runner.invoke(args=["setup-local-db"])

    assert result.exit_code != 0
    assert "Error: setup-local-db is restricted to local SQLite databases." in result.output
    assert "Refusing to run." in result.output


def test_setup_local_db_create_all_fallback(tmp_path: Path) -> None:
    """Verify setup-local-db handles pre-existing tables created without Alembic version table."""
    db_file = tmp_path / "studysphere_create_all.db"
    app = _create_sqlite_test_app(db_file)

    with app.app_context():
        # Pre-create tables directly via SQLAlchemy metadata without alembic_version
        db.create_all()

    runner = app.test_cli_runner()
    topic_count, _, _ = _data_counts()
    result = runner.invoke(args=["setup-local-db"])

    assert result.exit_code == 0
    assert "Local SQLite database setup completed successfully!" in result.output

    with app.app_context():
        assert Course.query.count() == 44
        assert Topic.query.count() == topic_count
        assert (
            Topic.query.filter(Topic.content.isnot(None), Topic.content != "").count()
            == topic_count
        )
