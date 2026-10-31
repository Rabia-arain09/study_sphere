"""Unit and integration tests for the study notes loader and notes-status commands."""

from pathlib import Path
import pytest
from app.extensions import db
from app.models import Course, Topic
from app.models.topic import ContentSource
from app.services.notes_loader import (
    NotesLoader,
    NotesValidationError,
    MissingNotesDirectoryError,
    load_notes,
    get_notes_status,
)


def _write_note(
    path: Path,
    subject: str = "Machine Learning",
    topic: str = "Introduction to Machine Learning",
    semester: int = 5,
    week: str = "1",
    difficulty: int = 1,
    content_source: str = "ai_generated",
    content_reviewed: bool = False,
    body: str = "# Introduction to Machine Learning\n\nStudy note content.",
) -> None:
    """Helper to write a note file with YAML front matter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rev_str = "true" if content_reviewed else "false"
    content = (
        f"---\n"
        f"subject: {subject}\n"
        f"topic: \"{topic}\"\n"
        f"semester: {semester}\n"
        f"week: \"{week}\"\n"
        f"difficulty: {difficulty}\n"
        f"content_source: {content_source}\n"
        f"content_reviewed: {rev_str}\n"
        f"---\n\n"
        f"{body}\n"
    )
    path.write_text(content, encoding="utf-8")


def _seed_test_course_and_topics(session) -> tuple[Course, list[Topic]]:
    """Seed sample Course and Topic records in the database."""
    course = Course(
        code="CS301",
        title="Machine Learning",
        semester=5,
        domain="Computing Core",
        credit_hours=3,
        contact_hours="3-0",
        is_elective=False,
    )
    session.add(course)
    session.flush()

    topic1 = Topic(
        course_id=course.id,
        semester=5,
        subject="Machine Learning",
        name="Introduction to Machine Learning",
        difficulty=1,
        week="1",
        description="Intro to ML",
    )
    topic2 = Topic(
        course_id=course.id,
        semester=5,
        subject="Machine Learning",
        name="Supervised Learning Foundations",
        difficulty=2,
        week="2",
        description="Supervised learning",
    )
    session.add_all([topic1, topic2])
    session.commit()
    return course, [topic1, topic2]


def test_missing_notes_dir_raises_error(app, tmp_path):
    """Verify MissingNotesDirectoryError is raised when the notes directory does not exist."""
    with app.app_context():
        non_existent = tmp_path / "does_not_exist"
        with pytest.raises(MissingNotesDirectoryError) as exc_info:
            load_notes(notes_dir=non_existent)

        err_msg = str(exc_info.value)
        assert "Missing notes folder" in err_msg
        assert str(non_existent) in err_msg


def test_no_markdown_files_raises_validation_error(app, tmp_path):
    """Verify NotesValidationError is raised when notes directory contains no .md files."""
    with app.app_context():
        empty_dir = tmp_path / "empty_notes"
        empty_dir.mkdir()
        with pytest.raises(NotesValidationError) as exc_info:
            load_notes(notes_dir=empty_dir)

        err_msg = str(exc_info.value)
        assert "No markdown (.md) note files found" in err_msg


def test_valid_load_and_field_assignment(app, tmp_path):
    """Verify valid note files are parsed and update topic content, content_source, and content_reviewed."""
    with app.app_context():
        _seed_test_course_and_topics(db.session)

        notes_dir = tmp_path / "notes"
        _write_note(
            notes_dir / "ml" / "01-intro.md",
            topic="Introduction to Machine Learning",
            content_source="lecture",
            content_reviewed=False,
            body="# Intro\n\nLecture notes here.",
        )
        _write_note(
            notes_dir / "ml" / "02-supervised.md",
            topic="Supervised Learning Foundations",
            content_source="ai_generated",
            content_reviewed=True,
            body="# Supervised\n\nAI generated notes.",
        )

        summary = load_notes(notes_dir=notes_dir)
        assert summary.total_files == 2
        assert summary.updated == 2
        assert summary.unchanged == 0
        assert summary.skipped == 0
        assert not summary.dry_run

        t1 = Topic.query.filter_by(name="Introduction to Machine Learning").one()
        assert t1.content == "# Intro\n\nLecture notes here."
        assert t1.content_source == ContentSource.LECTURE
        assert t1.content_reviewed is False

        t2 = Topic.query.filter_by(name="Supervised Learning Foundations").one()
        assert t2.content == "# Supervised\n\nAI generated notes."
        assert t2.content_source == ContentSource.AI_GENERATED
        assert t2.content_reviewed is True


def test_idempotent_loading(app, tmp_path):
    """Verify loading twice without file changes updates on first run and reports unchanged on second."""
    with app.app_context():
        _seed_test_course_and_topics(db.session)
        notes_dir = tmp_path / "notes"
        _write_note(notes_dir / "ml" / "01-intro.md")
        _write_note(
            notes_dir / "ml" / "02-supervised.md",
            topic="Supervised Learning Foundations",
        )

        first_run = load_notes(notes_dir=notes_dir)
        assert first_run.updated == 2
        assert first_run.unchanged == 0
        assert first_run.skipped == 0

        second_run = load_notes(notes_dir=notes_dir)
        assert second_run.updated == 0
        assert second_run.unchanged == 2
        assert second_run.skipped == 0


def test_missing_front_matter_key_validation(app, tmp_path):
    """Verify missing required front matter key raises NotesValidationError with file name and writes nothing."""
    with app.app_context():
        _seed_test_course_and_topics(db.session)
        notes_dir = tmp_path / "notes"
        bad_file = notes_dir / "ml" / "01-missing-key.md"
        bad_file.parent.mkdir(parents=True, exist_ok=True)
        # Omit content_source
        bad_file.write_text(
            "---\n"
            "subject: Machine Learning\n"
            "topic: \"Introduction to Machine Learning\"\n"
            "semester: 5\n"
            "week: \"1\"\n"
            "difficulty: 1\n"
            "content_reviewed: false\n"
            "---\n\n"
            "# Content\n",
            encoding="utf-8",
        )

        with pytest.raises(NotesValidationError) as exc_info:
            load_notes(notes_dir=notes_dir)

        err_msg = str(exc_info.value)
        assert "01-missing-key.md" in err_msg
        assert "Missing required front matter key: 'content_source'" in err_msg

        # Verify nothing was written to the database
        t = Topic.query.filter_by(name="Introduction to Machine Learning").one()
        assert t.content is None


def test_unknown_topic_validation(app, tmp_path):
    """Verify referencing a topic not present in the database raises NotesValidationError and writes nothing."""
    with app.app_context():
        _seed_test_course_and_topics(db.session)
        notes_dir = tmp_path / "notes"
        _write_note(
            notes_dir / "ml" / "01-unknown.md",
            topic="Quantum Deep Learning Unknown",
        )

        with pytest.raises(NotesValidationError) as exc_info:
            load_notes(notes_dir=notes_dir)

        err_msg = str(exc_info.value)
        assert "01-unknown.md" in err_msg
        assert "Topic not found in database" in err_msg
        assert "Quantum Deep Learning Unknown" in err_msg

        t = Topic.query.filter_by(name="Introduction to Machine Learning").one()
        assert t.content is None


def test_duplicate_topic_files_validation(app, tmp_path):
    """Verify that multiple note files targeting the same topic raise NotesValidationError and write nothing."""
    with app.app_context():
        _seed_test_course_and_topics(db.session)
        notes_dir = tmp_path / "notes"
        _write_note(notes_dir / "ml" / "01-first.md", topic="Introduction to Machine Learning")
        _write_note(notes_dir / "ml" / "01-second.md", topic="Introduction to Machine Learning")

        with pytest.raises(NotesValidationError) as exc_info:
            load_notes(notes_dir=notes_dir)

        err_msg = str(exc_info.value)
        assert "Duplicate note file for topic" in err_msg
        assert "01-second.md" in err_msg
        assert "01-first.md" in err_msg

        t = Topic.query.filter_by(name="Introduction to Machine Learning").one()
        assert t.content is None


def test_invalid_content_source_validation(app, tmp_path):
    """Verify that an invalid content_source raises NotesValidationError and writes nothing."""
    with app.app_context():
        _seed_test_course_and_topics(db.session)
        notes_dir = tmp_path / "notes"
        _write_note(
            notes_dir / "ml" / "01-invalid-source.md",
            content_source="wikipedia_scraping",
        )

        with pytest.raises(NotesValidationError) as exc_info:
            load_notes(notes_dir=notes_dir)

        err_msg = str(exc_info.value)
        assert "01-invalid-source.md" in err_msg
        assert "Invalid content_source 'wikipedia_scraping'" in err_msg


def test_empty_markdown_body_validation(app, tmp_path):
    """Verify that a note file with an empty body raises NotesValidationError and writes nothing."""
    with app.app_context():
        _seed_test_course_and_topics(db.session)
        notes_dir = tmp_path / "notes"
        _write_note(notes_dir / "ml" / "01-empty.md", body="   \n   \n")

        with pytest.raises(NotesValidationError) as exc_info:
            load_notes(notes_dir=notes_dir)

        err_msg = str(exc_info.value)
        assert "01-empty.md" in err_msg
        assert "Note body is empty" in err_msg


def test_reviewed_skip_and_force_behaviour(app, tmp_path):
    """Verify that content_reviewed=True in DB prevents overwrites unless --force is specified."""
    with app.app_context():
        _seed_test_course_and_topics(db.session)
        topic = Topic.query.filter_by(name="Introduction to Machine Learning").one()
        topic.content = "Original verified notes"
        topic.content_source = ContentSource.LECTURE
        topic.content_reviewed = True
        db.session.commit()

        notes_dir = tmp_path / "notes"
        _write_note(
            notes_dir / "ml" / "01-intro.md",
            topic="Introduction to Machine Learning",
            content_source="ai_generated",
            content_reviewed=False,
            body="New unverified AI notes",
        )

        # 1. Normal run without force: topic is skipped
        summary_skip = load_notes(notes_dir=notes_dir, force=False)
        assert summary_skip.skipped == 1
        assert summary_skip.updated == 0

        topic_db = Topic.query.filter_by(name="Introduction to Machine Learning").one()
        assert topic_db.content == "Original verified notes"
        assert topic_db.content_source == ContentSource.LECTURE
        assert topic_db.content_reviewed is True

        # 2. Run with force: topic is updated
        summary_force = load_notes(notes_dir=notes_dir, force=True)
        assert summary_force.skipped == 0
        assert summary_force.updated == 1

        topic_db_forced = Topic.query.filter_by(name="Introduction to Machine Learning").one()
        assert topic_db_forced.content == "New unverified AI notes"
        assert topic_db_forced.content_source == ContentSource.AI_GENERATED
        assert topic_db_forced.content_reviewed is False


def test_dry_run_writes_nothing(app, tmp_path):
    """Verify dry_run=True stages metrics in rolled-back transaction without saving."""
    with app.app_context():
        _seed_test_course_and_topics(db.session)
        notes_dir = tmp_path / "notes"
        _write_note(notes_dir / "ml" / "01-intro.md")
        _write_note(
            notes_dir / "ml" / "02-supervised.md",
            topic="Supervised Learning Foundations",
        )

        summary = load_notes(notes_dir=notes_dir, dry_run=True)
        assert summary.dry_run is True
        assert summary.updated == 2
        assert summary.total_files == 2

        # Verify DB is untouched
        topics = Topic.query.all()
        for t in topics:
            assert t.content is None


def test_notes_status_query_and_formatting(app, tmp_path):
    """Verify get_notes_status aggregates totals and formats output accurately."""
    with app.app_context():
        _seed_test_course_and_topics(db.session)

        # Status before notes
        status_before = get_notes_status()
        assert status_before.total_topics == 2
        assert status_before.total_with_notes == 0
        assert status_before.total_reviewed == 0

        # Load notes
        notes_dir = tmp_path / "notes"
        _write_note(
            notes_dir / "ml" / "01-intro.md",
            topic="Introduction to Machine Learning",
            content_source="lecture",
            content_reviewed=True,
        )
        _write_note(
            notes_dir / "ml" / "02-supervised.md",
            topic="Supervised Learning Foundations",
            content_source="ai_generated",
            content_reviewed=False,
        )
        load_notes(notes_dir=notes_dir)

        status_after = get_notes_status()
        assert status_after.total_topics == 2
        assert status_after.total_with_notes == 2
        assert status_after.total_reviewed == 1
        assert status_after.total_ai_generated == 1
        assert status_after.total_lecture == 1

        formatted = status_after.format_cli_output()
        assert "Machine Learning" in formatted
        assert "Total" in formatted


def test_cli_load_notes_command(app, tmp_path):
    """Verify load-notes Flask CLI command execution and options."""
    with app.app_context():
        _seed_test_course_and_topics(db.session)
        notes_dir = tmp_path / "notes"
        _write_note(notes_dir / "ml" / "01-intro.md")
        _write_note(
            notes_dir / "ml" / "02-supervised.md",
            topic="Supervised Learning Foundations",
        )

        runner = app.test_cli_runner()
        # Test dry-run
        result_dry = runner.invoke(args=["load-notes", "--notes-dir", str(notes_dir), "--dry-run"])
        assert result_dry.exit_code == 0
        assert "DRY RUN" in result_dry.output

        # Test actual load
        result = runner.invoke(args=["load-notes", "--notes-dir", str(notes_dir)])
        assert result.exit_code == 0
        assert "Updated         : 2" in result.output
        assert "Committed successfully" in result.output


def test_cli_load_notes_errors_exit_nonzero(app, tmp_path):
    """Verify load-notes command exits non-zero on missing directory or validation error."""
    with app.app_context():
        runner = app.test_cli_runner()

        # Missing directory
        res_missing = runner.invoke(args=["load-notes", "--notes-dir", str(tmp_path / "absent")])
        assert res_missing.exit_code != 0
        assert "Missing notes folder" in res_missing.output

        # Validation error (missing key)
        notes_dir = tmp_path / "invalid_notes"
        bad_file = notes_dir / "ml" / "01-bad.md"
        bad_file.parent.mkdir(parents=True, exist_ok=True)
        bad_file.write_text(
            "---\n"
            "subject: Machine Learning\n"
            "topic: \"Introduction to Machine Learning\"\n"
            "---\n\n"
            "# Bad\n",
            encoding="utf-8",
        )
        res_invalid = runner.invoke(args=["load-notes", "--notes-dir", str(notes_dir)])
        assert res_invalid.exit_code != 0
        assert "Notes validation failed" in res_invalid.output


def test_cli_notes_status_command(app, tmp_path):
    """Verify notes-status Flask CLI command outputs subject breakdown."""
    with app.app_context():
        _seed_test_course_and_topics(db.session)
        notes_dir = tmp_path / "notes"
        _write_note(notes_dir / "ml" / "01-intro.md")
        load_notes(notes_dir=notes_dir)

        runner = app.test_cli_runner()
        result = runner.invoke(args=["notes-status"])
        assert result.exit_code == 0
        assert "StudySphere Study Notes Status" in result.output
        assert "Machine Learning" in result.output
        assert "Total" in result.output
