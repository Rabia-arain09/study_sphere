"""Unit and integration tests for the curriculum loader service."""

from pathlib import Path
import pytest
from app.extensions import db
from app.models import Course, CoursePrerequisite, Topic, Prerequisite
from app.services.curriculum_loader import (
    CurriculumLoader,
    CurriculumValidationError,
    MissingDataFileError,
    load_curriculum,
)


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    """Helper to write CSV file with utf-8-sig encoding."""
    import csv

    with open(path, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def _setup_minimal_curriculum_dir(dir_path: Path) -> None:
    """Create a minimal valid set of 4 curriculum CSVs."""
    _write_csv(
        dir_path / "courses.csv",
        ["semester", "course_code", "title", "domain", "credit_hours", "contact_hours", "is_elective"],
        [
            ["1", "CS101", "Programming Fundamentals", "Computing Core", "4", "3-3", "0"],
            ["2", "CS102", "Object Oriented Programming", "Computing Core", "4", "3-3", "0"],
        ],
    )
    _write_csv(
        dir_path / "course_prerequisites.csv",
        ["course_code", "prerequisite_code"],
        [
            ["CS102", "CS101"],
        ],
    )
    _write_csv(
        dir_path / "topics.csv",
        ["semester", "subject", "course_code", "week", "topic", "difficulty", "tags", "description"],
        [
            ["1", "Programming Fundamentals", "CS101", "1", "Variables and Types", "1", "vars;syntax", "Intro vars"],
            ["1", "Programming Fundamentals", "CS101", "2", "Control Flow", "2", "loops;conditions", "Intro flow"],
        ],
    )
    _write_csv(
        dir_path / "topic_prerequisites.csv",
        ["subject", "topic", "prerequisite_subject", "prerequisite_topic"],
        [
            ["Programming Fundamentals", "Control Flow", "Programming Fundamentals", "Variables and Types"],
        ],
    )


def test_missing_data_file_raises_error(app, tmp_path):
    """Verify that MissingDataFileError is raised and identifies the missing file."""
    with app.app_context():
        # Directory has no CSVs
        with pytest.raises(MissingDataFileError) as exc_info:
            load_curriculum(data_dir=tmp_path)

        err_msg = str(exc_info.value)
        assert "Missing required data file" in err_msg
        assert "courses.csv" in err_msg


def test_missing_required_column_validation(app, tmp_path):
    """Verify that validation flags missing required header columns."""
    with app.app_context():
        _setup_minimal_curriculum_dir(tmp_path)
        # Corrupt courses.csv header by omitting credit_hours
        _write_csv(
            tmp_path / "courses.csv",
            ["semester", "course_code", "title", "domain", "contact_hours", "is_elective"],
            [["1", "CS101", "Programming Fundamentals", "Computing Core", "3-3", "0"]],
        )

        with pytest.raises(CurriculumValidationError) as exc_info:
            load_curriculum(data_dir=tmp_path)

        assert "missing required column(s)" in str(exc_info.value).lower()
        assert "credit_hours" in str(exc_info.value)


def test_invalid_difficulty_validation(app, tmp_path):
    """Verify that difficulty outside 1-5 is rejected."""
    with app.app_context():
        _setup_minimal_curriculum_dir(tmp_path)
        # Invalid difficulty 6
        _write_csv(
            tmp_path / "topics.csv",
            ["semester", "subject", "course_code", "week", "topic", "difficulty", "tags", "description"],
            [
                ["1", "Programming Fundamentals", "CS101", "1", "Variables", "6", "vars", "test"],
            ],
        )

        with pytest.raises(CurriculumValidationError) as exc_info:
            load_curriculum(data_dir=tmp_path)

        assert "difficulty must be between 1 and 5" in str(exc_info.value)


def test_duplicate_topic_in_subject_validation(app, tmp_path):
    """Verify that duplicate topic names within the same subject are rejected."""
    with app.app_context():
        _setup_minimal_curriculum_dir(tmp_path)
        _write_csv(
            tmp_path / "topics.csv",
            ["semester", "subject", "course_code", "week", "topic", "difficulty", "tags", "description"],
            [
                ["1", "Programming Fundamentals", "CS101", "1", "Variables", "1", "vars", "desc 1"],
                ["1", "Programming Fundamentals", "CS101", "2", "Variables", "2", "vars", "desc 2"],
            ],
        )

        with pytest.raises(CurriculumValidationError) as exc_info:
            load_curriculum(data_dir=tmp_path)

        assert "duplicate topic name 'Variables'" in str(exc_info.value)


def test_unknown_course_and_topic_references(app, tmp_path):
    """Verify that references to non-existent courses or topics trigger validation errors."""
    with app.app_context():
        _setup_minimal_curriculum_dir(tmp_path)
        # Course prereq referencing non-existent CS999
        _write_csv(
            tmp_path / "course_prerequisites.csv",
            ["course_code", "prerequisite_code"],
            [["CS102", "CS999"]],
        )

        with pytest.raises(CurriculumValidationError) as exc_info:
            load_curriculum(data_dir=tmp_path)

        assert "unknown prerequisite_code 'CS999'" in str(exc_info.value)


def test_self_link_detection(app, tmp_path):
    """Verify that self-referencing prerequisites are caught and rejected."""
    with app.app_context():
        _setup_minimal_curriculum_dir(tmp_path)
        _write_csv(
            tmp_path / "course_prerequisites.csv",
            ["course_code", "prerequisite_code"],
            [["CS101", "CS101"]],
        )

        with pytest.raises(CurriculumValidationError) as exc_info:
            load_curriculum(data_dir=tmp_path)

        assert "self-prerequisite detected on 'CS101'" in str(exc_info.value)


def test_cycle_detection_in_course_prerequisites(app, tmp_path):
    """Verify cycle detection in course prerequisite graph."""
    with app.app_context():
        _setup_minimal_curriculum_dir(tmp_path)
        # Add a cycle: CS102 -> CS101 and CS101 -> CS102
        _write_csv(
            tmp_path / "course_prerequisites.csv",
            ["course_code", "prerequisite_code"],
            [
                ["CS102", "CS101"],
                ["CS101", "CS102"],
            ],
        )

        with pytest.raises(CurriculumValidationError) as exc_info:
            load_curriculum(data_dir=tmp_path)

        assert "Cycle detected in course prerequisites" in str(exc_info.value)


def test_cycle_detection_in_topic_prerequisites(app, tmp_path):
    """Verify cycle detection in topic prerequisite graph."""
    with app.app_context():
        _setup_minimal_curriculum_dir(tmp_path)
        _write_csv(
            tmp_path / "topic_prerequisites.csv",
            ["subject", "topic", "prerequisite_subject", "prerequisite_topic"],
            [
                ["Programming Fundamentals", "Control Flow", "Programming Fundamentals", "Variables and Types"],
                ["Programming Fundamentals", "Variables and Types", "Programming Fundamentals", "Control Flow"],
            ],
        )

        with pytest.raises(CurriculumValidationError) as exc_info:
            load_curriculum(data_dir=tmp_path)

        assert "Cycle detected in topic prerequisites" in str(exc_info.value)


def test_dry_run_mode(app):
    """Verify dry-run mode validates data and computes counts without persisting any rows."""
    with app.app_context():
        summary = load_curriculum(data_dir="data", dry_run=True)
        assert summary.dry_run is True
        assert summary.courses_count == 44
        assert summary.course_prerequisites_count == 12
        assert summary.topics_count == 165
        assert summary.topic_prerequisites_count == 194

        # Confirm nothing was written
        assert Course.query.count() == 0
        assert CoursePrerequisite.query.count() == 0
        assert Topic.query.count() == 0
        assert Prerequisite.query.count() == 0


def test_idempotency_and_real_csv_integration(app):
    """Integration test loading real CSVs: exactly 44/12/165/194 and idempotent on second run."""
    with app.app_context():
        # First execution: loads real CSVs
        summary1 = load_curriculum(data_dir="data", dry_run=False)
        assert summary1.courses_count == 44
        assert summary1.course_prerequisites_count == 12
        assert summary1.topics_count == 165
        assert summary1.topic_prerequisites_count == 194

        assert Course.query.count() == 44
        assert CoursePrerequisite.query.count() == 12
        assert Topic.query.count() == 165
        assert Prerequisite.query.count() == 194

        # Verify parsed properties
        ml_topic = Topic.query.filter_by(name="Introduction to Machine Learning").first()
        assert ml_topic is not None
        assert ml_topic.difficulty == 1
        assert ml_topic.tags == ["machine learning", "supervised", "unsupervised", "reinforcement"]
        assert ml_topic.course.title == "Machine Learning"

        cs102 = Course.query.filter_by(code="CS102").first()
        assert cs102 is not None
        assert cs102.title == "Programming Fundamentals"
        assert cs102.contact_hours == "3-3"
        assert cs102.credit_hours == 4

        # Second execution: asserts idempotency (no duplicate key errors, row counts unchanged)
        summary2 = load_curriculum(data_dir="data", dry_run=False)
        assert summary2.courses_count == 44
        assert summary2.course_prerequisites_count == 12
        assert summary2.topics_count == 165
        assert summary2.topic_prerequisites_count == 194

        assert Course.query.count() == 44
        assert CoursePrerequisite.query.count() == 12
        assert Topic.query.count() == 165
        assert Prerequisite.query.count() == 194
