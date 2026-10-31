"""Study notes loader service for parsing, validating, and ingesting Markdown study notes."""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING
import yaml
from sqlalchemy import case, func
from sqlalchemy.orm import Session
from app.extensions import db
from app.models.topic import ContentSource, Topic

REQUIRED_FRONT_MATTER_KEYS: tuple[str, ...] = (
    "subject",
    "topic",
    "semester",
    "week",
    "difficulty",
    "content_source",
    "content_reviewed",
)

VALID_CONTENT_SOURCES: set[str] = {
    ContentSource.LECTURE.value,
    ContentSource.AI_GENERATED.value,
}


class NotesLoaderError(Exception):
    """Base exception for study notes loading operations."""


class MissingNotesDirectoryError(NotesLoaderError):
    """Raised when the specified notes directory or required subject folder is missing."""

    def __init__(self, path: Path | str) -> None:
        expected = Path(path).resolve()
        super().__init__(
            f"Missing notes folder '{path}'. It must be placed at '{expected}'."
        )


class NotesValidationError(NotesLoaderError):
    """Raised when one or more note files fail structural or referential validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        message = (
            f"Notes validation failed with {len(errors)} error(s):\n"
            + "\n".join(f"  - {err}" for err in errors)
        )
        super().__init__(message)


@dataclass
class ParsedNote:
    """Represents a validated, parsed markdown note file."""

    file_path: Path
    semester: int
    subject: str
    topic: str
    week: str
    difficulty: int
    content_source: str
    content_reviewed: bool
    body: str

    @property
    def topic_key(self) -> tuple[int, str, str]:
        """Unique compound key matching Topic natural key: (semester, subject, name)."""
        return (self.semester, self.subject, self.topic)


@dataclass
class NotesSummary:
    """Summary metrics of a study notes loading execution."""

    total_files: int
    updated: int
    unchanged: int
    skipped: int
    dry_run: bool = False
    notes_dir: str = "data/notes"
    skipped_topics: list[str] = field(default_factory=list)

    def format_cli_output(self) -> str:
        """Render a formatted multi-line summary table for terminal display."""
        status_line = (
            "DRY RUN (validated successfully, no changes persisted)"
            if self.dry_run
            else "Committed successfully"
        )
        lines = [
            "=" * 60,
            " StudySphere Notes Ingestion Summary",
            "=" * 60,
            f"> Notes Directory : {self.notes_dir}",
            f"> Files Inspected : {self.total_files}",
            f"> Transaction     : {status_line}",
            "-" * 60,
            f"  Updated         : {self.updated}",
            f"  Unchanged       : {self.unchanged}",
            f"  Skipped         : {self.skipped}",
            "=" * 60,
        ]
        if self.skipped > 0 and self.skipped_topics:
            lines.append(
                "Skipped topics (content_reviewed is True in database; use --force to overwrite):"
            )
            for item in self.skipped_topics:
                lines.append(f"  * {item}")
            lines.append("=" * 60)
        return "\n".join(lines)


@dataclass
class SubjectNotesStatus:
    """Aggregated study notes status for a single curriculum subject."""

    subject: str
    total_topics: int
    topics_with_notes: int
    notes_reviewed: int
    ai_generated: int
    lecture: int


@dataclass
class OverallNotesStatus:
    """Overall study notes inventory status across all curriculum subjects."""

    subjects: list[SubjectNotesStatus]
    total_topics: int
    total_with_notes: int
    total_reviewed: int
    total_ai_generated: int
    total_lecture: int

    def format_cli_output(self) -> str:
        """Render a clean tabular report for the notes-status command."""
        lines = [
            "=" * 84,
            " StudySphere Study Notes Status",
            "=" * 84,
            f"{'Subject':<28} {'Total Topics':>12} {'With Notes':>11} {'Reviewed':>10} {'AI Generated':>13} {'Lecture':>8}",
            "-" * 84,
        ]
        if not self.subjects:
            lines.append("No curriculum topics found in database.")
        else:
            for s in self.subjects:
                lines.append(
                    f"{s.subject:<28} {s.total_topics:>12} {s.topics_with_notes:>11} {s.notes_reviewed:>10} {s.ai_generated:>13} {s.lecture:>8}"
                )
            lines.append("-" * 84)
            lines.append(
                f"{'Total':<28} {self.total_topics:>12} {self.total_with_notes:>11} {self.total_reviewed:>10} {self.total_ai_generated:>13} {self.total_lecture:>8}"
            )
        lines.append("=" * 84)
        return "\n".join(lines)


class NotesLoader:
    """Service for discovering, validating, and idempotently loading Markdown study notes."""

    def __init__(
        self,
        notes_dir: str | Path = "data/notes",
        force: bool = False,
        session: Session | None = None,
    ) -> None:
        """Initialize the notes loader.

        Args:
            notes_dir: Root directory holding per-subject markdown notes.
            force: When True, overwrite topics even if content_reviewed is True in database.
            session: Optional SQLAlchemy session; defaults to db.session.
        """
        self.notes_dir: Path = Path(notes_dir)
        self.force: bool = force
        self.session: Session = session or db.session

    def discover_files(self) -> list[Path]:
        """Locate all markdown note files under the configured notes directory.

        Returns:
            list[Path]: Sorted list of markdown file paths.

        Raises:
            MissingNotesDirectoryError: If notes_dir or required subfolder is missing.
            NotesValidationError: If notes_dir is not a directory or contains no .md files.
        """
        if not self.notes_dir.exists():
            raise MissingNotesDirectoryError(self.notes_dir)

        if not self.notes_dir.is_dir():
            raise NotesValidationError(
                [f"Specified notes path '{self.notes_dir}' is not a directory."]
            )

        # When running against the default data/notes location, verify the canonical machine-learning folder
        resolved_notes = self.notes_dir.resolve()
        default_notes = Path("data/notes").resolve()
        if resolved_notes == default_notes:
            ml_folder = self.notes_dir / "machine-learning"
            if not ml_folder.exists() or not ml_folder.is_dir():
                raise MissingNotesDirectoryError(ml_folder)

        files = sorted(
            p
            for p in self.notes_dir.rglob("*.md")
            if p.is_file() and not p.name.startswith(".")
        )
        if not files:
            raise NotesValidationError(
                [f"No markdown (.md) note files found in '{self.notes_dir}'."]
            )

        return files

    def parse_note_file(self, file_path: Path) -> tuple[ParsedNote | None, list[str]]:
        """Parse and validate YAML front matter and Markdown body from a note file.

        Args:
            file_path: Path to the note file.

        Returns:
            tuple[ParsedNote | None, list[str]]: Parsed note instance (or None) and list of error strings.
        """
        errors: list[str] = []
        try:
            raw_text = file_path.read_text(encoding="utf-8")
        except Exception as exc:
            return None, [f"[{file_path}] Failed to read file: {exc}"]

        text = raw_text.lstrip("\ufeff")
        if not text.startswith("---"):
            return None, [
                f"[{file_path}] File must begin with YAML front matter delimiter '---'."
            ]

        parts = text.split("---", 2)
        if len(parts) < 3:
            return None, [
                f"[{file_path}] Missing closing '---' delimiter for YAML front matter."
            ]

        if parts[0].strip() != "":
            errors.append(f"[{file_path}] Content found before opening '---' delimiter.")

        try:
            fm = yaml.safe_load(parts[1])
        except yaml.YAMLError as exc:
            return None, [f"[{file_path}] Invalid YAML front matter: {exc}"]

        if not isinstance(fm, dict):
            return None, [f"[{file_path}] Front matter must be a YAML dictionary mapping."]

        for key in REQUIRED_FRONT_MATTER_KEYS:
            if key not in fm or fm[key] is None:
                errors.append(f"[{file_path}] Missing required front matter key: '{key}'.")

        cs = fm.get("content_source")
        if cs not in VALID_CONTENT_SOURCES:
            errors.append(
                f"[{file_path}] Invalid content_source '{cs}'. Must be one of {sorted(VALID_CONTENT_SOURCES)}."
            )

        cr = fm.get("content_reviewed")
        if not isinstance(cr, bool):
            errors.append(
                f"[{file_path}] Invalid content_reviewed '{cr}'. Must be a boolean (true/false)."
            )

        semester_val = fm.get("semester")
        semester: int | None = None
        try:
            semester = int(semester_val)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            errors.append(
                f"[{file_path}] Semester must be an integer, got '{semester_val}'."
            )

        diff_val = fm.get("difficulty")
        diff: int | None = None
        try:
            diff = int(diff_val)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            errors.append(
                f"[{file_path}] Difficulty must be an integer, got '{diff_val}'."
            )

        subject = str(fm.get("subject", "")).strip()
        topic_name = str(fm.get("topic", "")).strip()
        if not subject:
            errors.append(f"[{file_path}] 'subject' cannot be empty.")
        if not topic_name:
            errors.append(f"[{file_path}] 'topic' cannot be empty.")

        body = parts[2].strip().replace("\r\n", "\n")
        if not body:
            errors.append(
                f"[{file_path}] Note body is empty. A non-empty markdown body is required."
            )

        if errors:
            return None, errors

        parsed = ParsedNote(
            file_path=file_path,
            semester=semester,  # type: ignore[arg-type]
            subject=subject,
            topic=topic_name,
            week=str(fm.get("week", "")).strip(),
            difficulty=diff,  # type: ignore[arg-type]
            content_source=str(cs),
            content_reviewed=bool(cr),
            body=body,
        )
        return parsed, []

    def validate_and_parse(
        self, files: list[Path]
    ) -> tuple[list[ParsedNote], dict[tuple[int, str, str], Topic]]:
        """Parse all note files and validate against duplicate topics and database referential integrity.

        Args:
            files: List of file paths to parse.

        Returns:
            tuple: (List of parsed notes, Mapping from (semester, subject, name) to Topic).

        Raises:
            NotesValidationError: If any file fails front matter or database validation.
        """
        all_errors: list[str] = []
        parsed_notes: list[ParsedNote] = []
        seen_topics: dict[tuple[int, str, str], Path] = {}

        for file_path in files:
            note, errors = self.parse_note_file(file_path)
            if errors:
                all_errors.extend(errors)
            elif note is not None:
                parsed_notes.append(note)
                key = note.topic_key
                if key in seen_topics:
                    all_errors.append(
                        f"[{file_path}] Duplicate note file for topic "
                        f"(semester={key[0]}, subject='{key[1]}', topic='{key[2]}'). "
                        f"Also defined in '{seen_topics[key]}'."
                    )
                else:
                    seen_topics[key] = file_path

        # Query all existing topics from the database
        topic_rows = self.session.query(Topic).all()
        topic_map: dict[tuple[int, str, str], Topic] = {
            (t.semester, t.subject, t.name): t for t in topic_rows
        }

        # Check referential integrity: every note must match an existing Topic
        for note in parsed_notes:
            if note.topic_key not in topic_map:
                all_errors.append(
                    f"[{note.file_path}] Topic not found in database: "
                    f"semester={note.semester}, subject='{note.subject}', topic='{note.topic}'."
                )

        if all_errors:
            raise NotesValidationError(all_errors)

        return parsed_notes, topic_map

    def load(self, dry_run: bool = False) -> NotesSummary:
        """Idempotently ingest study notes into the database in a single transaction.

        Args:
            dry_run: When True, stages changes in a rolled-back transaction without saving.

        Returns:
            NotesSummary: Summary of updated, unchanged, and skipped records.

        Raises:
            NotesLoaderError: On validation, file discovery, or transactional failure.
        """
        files = self.discover_files()
        notes, topic_map = self.validate_and_parse(files)

        updated = 0
        unchanged = 0
        skipped = 0
        skipped_topics: list[str] = []

        try:
            for note in notes:
                topic = topic_map[note.topic_key]

                # Never overwrite a topic whose content_reviewed is already True unless --force is given
                if topic.content_reviewed and not self.force:
                    skipped += 1
                    skipped_topics.append(
                        f"{topic.subject} -> {topic.name} ({note.file_path.name})"
                    )
                    continue

                target_content = note.body
                target_source = ContentSource(note.content_source)
                target_reviewed = note.content_reviewed

                existing_content = (
                    topic.content.strip().replace("\r\n", "\n")
                    if topic.content is not None
                    else None
                )

                has_changed = (
                    existing_content != target_content
                    or topic.content_source != target_source
                    or topic.content_reviewed != target_reviewed
                )

                if has_changed:
                    topic.content = target_content
                    topic.content_source = target_source
                    topic.content_reviewed = target_reviewed
                    updated += 1
                else:
                    unchanged += 1

            if dry_run:
                self.session.rollback()
            else:
                self.session.commit()

        except Exception:
            self.session.rollback()
            raise

        return NotesSummary(
            total_files=len(files),
            updated=updated,
            unchanged=unchanged,
            skipped=skipped,
            dry_run=dry_run,
            notes_dir=str(self.notes_dir),
            skipped_topics=skipped_topics,
        )


def load_notes(
    notes_dir: str | Path = "data/notes",
    force: bool = False,
    dry_run: bool = False,
    session: Session | None = None,
) -> NotesSummary:
    """Convenience wrapper to instantiate NotesLoader and ingest study notes.

    Args:
        notes_dir: Root notes directory (default: data/notes).
        force: Force overwriting topics where content_reviewed is already True.
        dry_run: Validate and stage without committing.
        session: Optional SQLAlchemy session.

    Returns:
        NotesSummary: Execution metrics.
    """
    loader = NotesLoader(notes_dir=notes_dir, force=force, session=session)
    return loader.load(dry_run=dry_run)


def get_notes_status(session: Session | None = None) -> OverallNotesStatus:
    """Aggregate study notes metrics across curriculum subjects from the database.

    Args:
        session: Optional SQLAlchemy session.

    Returns:
        OverallNotesStatus: Aggregated per-subject and total statistics.
    """
    sess: Session = session or db.session

    rows = (
        sess.query(
            Topic.subject,
            func.count(Topic.id).label("total_topics"),
            func.count(
                case((Topic.content.isnot(None) & (Topic.content != ""), 1))
            ).label("with_notes"),
            func.count(
                case(
                    (
                        Topic.content.isnot(None)
                        & (Topic.content != "")
                        & (Topic.content_reviewed == True),
                        1,
                    )
                )
            ).label("reviewed"),
            func.count(
                case(
                    (
                        Topic.content.isnot(None)
                        & (Topic.content != "")
                        & (Topic.content_source == ContentSource.AI_GENERATED),
                        1,
                    )
                )
            ).label("ai_generated"),
            func.count(
                case(
                    (
                        Topic.content.isnot(None)
                        & (Topic.content != "")
                        & (Topic.content_source == ContentSource.LECTURE),
                        1,
                    )
                )
            ).label("lecture"),
        )
        .group_by(Topic.subject)
        .order_by(Topic.subject)
        .all()
    )

    subjects: list[SubjectNotesStatus] = []
    tot_topics = 0
    tot_with_notes = 0
    tot_reviewed = 0
    tot_ai = 0
    tot_lecture = 0

    for r in rows:
        subj = SubjectNotesStatus(
            subject=r.subject,
            total_topics=int(r.total_topics),
            topics_with_notes=int(r.with_notes),
            notes_reviewed=int(r.reviewed),
            ai_generated=int(r.ai_generated),
            lecture=int(r.lecture),
        )
        subjects.append(subj)
        tot_topics += subj.total_topics
        tot_with_notes += subj.topics_with_notes
        tot_reviewed += subj.notes_reviewed
        tot_ai += subj.ai_generated
        tot_lecture += subj.lecture

    return OverallNotesStatus(
        subjects=subjects,
        total_topics=tot_topics,
        total_with_notes=tot_with_notes,
        total_reviewed=tot_reviewed,
        total_ai_generated=tot_ai,
        total_lecture=tot_lecture,
    )
