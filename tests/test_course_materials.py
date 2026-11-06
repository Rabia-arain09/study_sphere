"""Tests for the per-course study notes and generated question banks."""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from app.extensions import db
from app.models import ContentSource, Question, QuestionSource, Topic
from app.services.curriculum_loader import load_curriculum
from app.services.notes_loader import NotesLoader
from app.services.question_loader import QuestionLoader

COMPLETED_SEMESTER = 3
LEGACY_SEMESTER_FIVE_CODES = {"CS301", "CS302", "CS3xx-E1", "CS3xx-E2"}
EXCLUDED_COURSE_CODES = {"SS401", "MT101", "MT150"}
LEGACY_SEMESTER_FIVE_SUBJECTS = {
    "Operating Systems",
    "Compiler Construction",
    "Machine Learning",
    "Web Engineering",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV file with optional BOM."""
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _slugify(value: str) -> str:
    """Convert a course title to the note and question folder convention."""
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _note_front_matter(path: Path) -> dict[str, object]:
    """Parse the YAML front matter from a Markdown note."""
    content = path.read_text(encoding="utf-8")
    _, front_matter, _ = content.split("---", maxsplit=2)
    parsed = yaml.safe_load(front_matter)
    assert isinstance(parsed, dict)
    return parsed


def _eligible_courses() -> list[dict[str, str]]:
    """Return named, in-scope courses through the currently completed semester."""
    courses = _read_csv(Path("data/courses.csv"))
    return [
        course
        for course in courses
        if int(course["semester"]) <= COMPLETED_SEMESTER
        and course["course_code"] not in EXCLUDED_COURSE_CODES
        and not (
            course["is_elective"] == "1"
            and course["title"].lower().startswith("elective")
        )
        and course["course_code"] not in LEGACY_SEMESTER_FIVE_CODES
    ]


def test_new_course_notes_and_question_banks_are_complete() -> None:
    """Verify every eligible new topic has a short note and six generated questions."""
    topics = _read_csv(Path("data/topics.csv"))
    prerequisites = _read_csv(Path("data/topic_prerequisites.csv"))
    notes_by_key: dict[tuple[str, str], list[Path]] = defaultdict(list)
    for path in Path("data/notes").rglob("*.md"):
        metadata = _note_front_matter(path)
        notes_by_key[(str(metadata.get("subject")), str(metadata.get("topic")))].append(
            path
        )
    question_rows = {
        course["title"]: _read_csv(
            Path("data/questions") / f"{_slugify(course['title'])}.csv"
        )
        for course in _eligible_courses()
    }

    for course in _eligible_courses():
        subject = course["title"]
        course_topics = [
            row
            for row in topics
            if row["semester"] == course["semester"] and row["subject"] == subject
        ]
        assert 3 <= len(course_topics) <= 5

        course_prerequisites = [
            row for row in prerequisites if row["subject"] == subject
        ]
        assert 1 <= len(course_prerequisites) <= 2
        topic_names = {row["topic"] for row in course_topics}
        assert all(
            row["topic"] in topic_names
            and row["prerequisite_subject"] == subject
            and row["prerequisite_topic"] in topic_names
            for row in course_prerequisites
        )

        for topic in course_topics:
            matching_notes = notes_by_key[(subject, topic["topic"])]
            assert len(matching_notes) == 1
            note_path = matching_notes[0]
            metadata = _note_front_matter(note_path)
            assert metadata["content_source"] == "ai_generated"
            assert metadata["content_reviewed"] is False
            note_body = note_path.read_text(encoding="utf-8").split(
                "---", maxsplit=2
            )[2]
            assert "**Definition:**" in note_body
            assert "## Key points" in note_body
            assert "## Example" in note_body

            matching_questions = [
                row
                for row in question_rows[subject]
                if row["semester"] == course["semester"]
                and row["topic"] == topic["topic"]
            ]
            assert len(matching_questions) == 6
            assert Counter(row["type"] for row in matching_questions) == {
                "mcq": 3,
                "tf": 1,
                "short": 1,
                "theory": 1,
            }
            assert all(row["source"] == "generated" for row in matching_questions)

    legacy_topics = [
        row for row in topics if row["subject"] in LEGACY_SEMESTER_FIVE_SUBJECTS
    ]
    assert len(legacy_topics) == 165


def test_new_course_materials_load_idempotently_and_keep_ai_flags(app) -> None:
    """Verify new material loads twice without duplicates or losing note metadata."""
    with app.app_context():
        load_curriculum()
        NotesLoader().load()
        question_files = sorted(Path("data/questions").glob("*.csv"))
        for question_file in question_files:
            QuestionLoader(question_file).load()

        new_topics = [
            row
            for row in _read_csv(Path("data/topics.csv"))
            if any(
                row["subject"] == course["title"]
                and row["semester"] == course["semester"]
                for course in _eligible_courses()
            )
        ]
        for row in new_topics:
            topic = Topic.query.filter_by(
                semester=int(row["semester"]),
                subject=row["subject"],
                name=row["topic"],
            ).one()
            assert topic.content_source == ContentSource.AI_GENERATED
            assert topic.content_reviewed is False
            assert len(topic.questions) == 6
            assert all(
                question.source == QuestionSource.GENERATED
                for question in topic.questions
            )

        first_counts = (
            Topic.query.count(),
            db.session.query(Question).count(),
        )
        load_curriculum()
        NotesLoader().load()
        for question_file in question_files:
            QuestionLoader(question_file).load()
        second_counts = (
            Topic.query.count(),
            db.session.query(Question).count(),
        )
        assert second_counts == first_counts
