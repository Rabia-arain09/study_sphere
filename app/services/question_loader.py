"""Question CSV ingestion and validation service for StudySphere assessment banks."""

from __future__ import annotations
import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from sqlalchemy.orm import Session
from app.extensions import db
from app.models.question import Question, QuestionType, QuestionSource
from app.models.topic import Topic


class QuestionLoaderError(Exception):
    """Base exception for question loader failures."""


class MissingQuestionsFileError(QuestionLoaderError):
    """Raised when the specified questions CSV file does not exist."""

    def __init__(self, file_path: Path) -> None:
        super().__init__(f"Questions CSV file not found at '{file_path}'.")


class QuestionsValidationError(QuestionLoaderError):
    """Raised when one or more question records fail validation checks."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        message = (
            f"Questions validation failed with {len(errors)} error(s):\n"
            + "\n".join(f"  - {err}" for err in errors)
        )
        super().__init__(message)


@dataclass
class ParsedQuestionRow:
    """Validated in-memory representation of a single question row."""

    row_index: int
    semester: int
    subject: str
    topic_name: str
    topic_id: int
    question_type: QuestionType
    question_text: str
    options: dict[str, str] | None
    correct_answer: str
    source: QuestionSource


@dataclass
class QuestionsSummary:
    """Execution metrics from a questions ingestion run."""

    total_rows: int
    inserted: int
    updated: int
    unchanged: int
    dry_run: bool = False
    csv_file: str = "data/questions.csv"

    def format_cli_output(self) -> str:
        """Render a formatted multi-line summary table for terminal display."""
        status_line = (
            "DRY RUN (validated successfully, no changes persisted)"
            if self.dry_run
            else "Committed successfully"
        )
        lines = [
            "=" * 60,
            " StudySphere Questions Ingestion Summary",
            "=" * 60,
            f"> Source File     : {self.csv_file}",
            f"> Records Read    : {self.total_rows}",
            f"> Transaction     : {status_line}",
            "-" * 60,
            f"  Inserted        : {self.inserted}",
            f"  Updated         : {self.updated}",
            f"  Unchanged       : {self.unchanged}",
            "=" * 60,
        ]
        return "\n".join(lines)


class QuestionLoader:
    """Validates and idempotently loads assessment questions from CSV files."""

    REQUIRED_COLUMNS: list[str] = [
        "semester",
        "subject",
        "topic",
        "type",
        "question_text",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
        "correct_answer",
        "source",
    ]

    def __init__(
        self,
        file_path: str | Path = "data/questions.csv",
        session: Session | None = None,
    ) -> None:
        """Initialize loader with file path and database session.

        Args:
            file_path: Path to target questions CSV.
            session: SQLAlchemy session (defaults to db.session).
        """
        self.file_path = Path(file_path)
        self.session = session or db.session

    def validate_and_parse(self) -> list[ParsedQuestionRow]:
        """Validate all rows in the CSV file against schema and referential integrity rules.

        Fails fast by accumulating all errors and aborting before any database modification.

        Returns:
            list[ParsedQuestionRow]: Validated question data ready for database staging.

        Raises:
            MissingQuestionsFileError: If CSV file is not found.
            QuestionsValidationError: If any row fails validation.
        """
        if not self.file_path.exists():
            raise MissingQuestionsFileError(self.file_path)

        # Preload topic natural key lookup mapping
        topics = self.session.query(Topic).all()
        topic_map: dict[tuple[int, str, str], Topic] = {
            (t.semester, t.subject.strip().lower(), t.name.strip().lower()): t
            for t in topics
        }

        all_errors: list[str] = []
        parsed_rows: list[ParsedQuestionRow] = []

        with open(self.file_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = [c.strip().lower() for c in (reader.fieldnames or [])]

            # Verify header columns
            missing_cols = [
                col for col in self.REQUIRED_COLUMNS if col not in fieldnames
            ]
            if missing_cols:
                raise QuestionsValidationError([
                    f"CSV header missing required column(s): {', '.join(missing_cols)}"
                ])

            for idx, raw_row in enumerate(reader, start=2):
                row = {
                    k.strip().lower(): (v.strip() if v else "")
                    for k, v in raw_row.items()
                    if k is not None
                }

                # 1. Semester validation
                sem_str = row.get("semester", "")
                semester: int | None = None
                try:
                    semester = int(sem_str)
                    if not (1 <= semester <= 8):
                        all_errors.append(
                            f"Row {idx}: 'semester' must be an integer between 1 and 8 (got '{sem_str}')."
                        )
                except ValueError:
                    all_errors.append(
                        f"Row {idx}: 'semester' must be an integer (got '{sem_str}')."
                    )

                # 2. Subject & Topic validation
                subject = row.get("subject", "")
                if not subject:
                    all_errors.append(f"Row {idx}: 'subject' cannot be empty.")

                topic_name = row.get("topic", "")
                if not topic_name:
                    all_errors.append(f"Row {idx}: 'topic' cannot be empty.")

                # Referential integrity check
                topic_entity: Topic | None = None
                if semester is not None and subject and topic_name:
                    lookup_key = (semester, subject.lower(), topic_name.lower())
                    topic_entity = topic_map.get(lookup_key)
                    if topic_entity is None:
                        all_errors.append(
                            f"Row {idx}: Topic not found in database: "
                            f"semester={semester}, subject='{subject}', topic='{topic_name}'."
                        )

                # 3. Question Type validation
                type_raw = row.get("type", "").lower()
                valid_types = {t.value: t for t in QuestionType}
                q_type = valid_types.get(type_raw)
                if q_type is None:
                    all_errors.append(
                        f"Row {idx}: Invalid question type '{type_raw}'. "
                        f"Must be one of: {', '.join(valid_types.keys())}."
                    )

                # 4. Question Text validation
                q_text = row.get("question_text", "")
                if not q_text:
                    all_errors.append(f"Row {idx}: 'question_text' cannot be empty.")

                # 5. Correct Answer validation
                correct_ans = row.get("correct_answer", "")
                if not correct_ans:
                    all_errors.append(f"Row {idx}: 'correct_answer' cannot be empty.")

                # 6. Type-specific option and answer validation
                options_dict: dict[str, str] | None = None
                if q_type == QuestionType.MCQ:
                    opt_a = row.get("option_a", "")
                    opt_b = row.get("option_b", "")
                    opt_c = row.get("option_c", "")
                    opt_d = row.get("option_d", "")

                    if not opt_a or not opt_b:
                        all_errors.append(
                            f"Row {idx}: MCQ questions require at least 'option_a' and 'option_b'."
                        )

                    options_dict = {"A": opt_a, "B": opt_b}
                    if opt_c:
                        options_dict["C"] = opt_c
                    if opt_d:
                        options_dict["D"] = opt_d

                    valid_keys = set(options_dict.keys())
                    valid_values = {v.lower() for v in options_dict.values()}
                    if (
                        correct_ans.upper() not in valid_keys
                        and correct_ans.lower() not in valid_values
                    ):
                        all_errors.append(
                            f"Row {idx}: MCQ 'correct_answer' '{correct_ans}' must match an option key "
                            f"({', '.join(sorted(valid_keys))}) or option text."
                        )
                elif q_type == QuestionType.TF:
                    if correct_ans.lower() not in ("true", "false"):
                        all_errors.append(
                            f"Row {idx}: True/False question 'correct_answer' must be 'True' or 'False' "
                            f"(got '{correct_ans}')."
                        )
                    options_dict = {"A": "True", "B": "False"}

                # 7. Source validation
                source_raw = row.get("source", "").lower() or "curriculum"
                valid_sources = {s.value: s for s in QuestionSource}
                q_source = valid_sources.get(source_raw)
                if q_source is None:
                    all_errors.append(
                        f"Row {idx}: Invalid question source '{source_raw}'. "
                        f"Must be one of: {', '.join(valid_sources.keys())}."
                    )

                if (
                    semester is not None
                    and topic_entity is not None
                    and q_type is not None
                    and q_text
                    and correct_ans
                    and q_source is not None
                ):
                    parsed_rows.append(
                        ParsedQuestionRow(
                            row_index=idx,
                            semester=semester,
                            subject=subject,
                            topic_name=topic_name,
                            topic_id=topic_entity.id,
                            question_type=q_type,
                            question_text=q_text,
                            options=options_dict,
                            correct_answer=correct_ans,
                            source=q_source,
                        )
                    )

        if all_errors:
            raise QuestionsValidationError(all_errors)

        return parsed_rows

    def load(self, dry_run: bool = False) -> QuestionsSummary:
        """Parse, validate, and idempotently persist questions to database.

        Args:
            dry_run: When True, stages changes in rolled-back transaction without saving.

        Returns:
            QuestionsSummary: Detailed counts of records processed, inserted, and updated.
        """
        parsed_rows = self.validate_and_parse()

        # Query existing questions for affected topics to ensure idempotency
        topic_ids = {r.topic_id for r in parsed_rows}
        existing_records = (
            self.session.query(Question)
            .filter(Question.topic_id.in_(topic_ids))
            .all()
        )
        existing_map: dict[tuple[int, str, str], Question] = {
            (
                q.topic_id,
                q.type.value if hasattr(q.type, "value") else str(q.type),
                q.question_text.strip(),
            ): q
            for q in existing_records
        }

        inserted = 0
        updated = 0
        unchanged = 0

        for row in parsed_rows:
            key = (row.topic_id, row.question_type.value, row.question_text.strip())
            existing = existing_map.get(key)

            if existing is None:
                new_q = Question(
                    topic_id=row.topic_id,
                    type=row.question_type,
                    question_text=row.question_text,
                    options=row.options,
                    correct_answer=row.correct_answer,
                    source=row.source,
                )
                self.session.add(new_q)
                existing_map[key] = new_q
                inserted += 1
            else:
                # Check if fields require updating
                changed = False
                if existing.options != row.options:
                    existing.options = row.options
                    changed = True
                if existing.correct_answer != row.correct_answer:
                    existing.correct_answer = row.correct_answer
                    changed = True
                if existing.source != row.source:
                    existing.source = row.source
                    changed = True

                if changed:
                    updated += 1
                else:
                    unchanged += 1

        if dry_run:
            self.session.rollback()
        else:
            self.session.commit()

        return QuestionsSummary(
            total_rows=len(parsed_rows),
            inserted=inserted,
            updated=updated,
            unchanged=unchanged,
            dry_run=dry_run,
            csv_file=str(self.file_path),
        )


def load_questions(
    file_path: str | Path = "data/questions.csv",
    dry_run: bool = False,
    session: Session | None = None,
) -> QuestionsSummary:
    """Convenience helper to validate and ingest question items from CSV."""
    loader = QuestionLoader(file_path=file_path, session=session)
    return loader.load(dry_run=dry_run)
