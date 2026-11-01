"""Test suite to validate the production assessment question bank CSV files."""

from __future__ import annotations

from pathlib import Path
from scripts.validate_questions import validate_questions_bank


def test_question_bank_csv_files_validation() -> None:
    """Verify that all subject question CSV files pass full schema and curriculum validation."""
    report = validate_questions_bank(
        questions_dir=Path("data/questions"),
        topics_csv_path=Path("data/topics.csv"),
    )

    # All error messages formatted clearly if validation fails
    error_summary = "\n".join(report.errors)
    assert report.is_valid, f"Question bank validation failed with errors:\n{error_summary}"
    assert report.total_topics == 165
    assert report.total_questions == 990
    assert len(report.errors) == 0
