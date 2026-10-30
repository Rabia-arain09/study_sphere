"""Curriculum loader service for parsing, validating, and ingesting syllabus CSVs."""

from __future__ import annotations
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from sqlalchemy.orm import Session
from app.extensions import db
from app.models import Course, CoursePrerequisite, Topic, Prerequisite


REQUIRED_DATA_FILES: tuple[str, ...] = (
    "courses.csv",
    "course_prerequisites.csv",
    "topics.csv",
    "topic_prerequisites.csv",
)

REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "courses.csv": (
        "semester",
        "course_code",
        "title",
        "domain",
        "credit_hours",
        "contact_hours",
        "is_elective",
    ),
    "course_prerequisites.csv": (
        "course_code",
        "prerequisite_code",
    ),
    "topics.csv": (
        "semester",
        "subject",
        "course_code",
        "week",
        "topic",
        "difficulty",
        "tags",
        "description",
    ),
    "topic_prerequisites.csv": (
        "subject",
        "topic",
        "prerequisite_subject",
        "prerequisite_topic",
    ),
}


class CurriculumLoaderError(Exception):
    """Base exception for curriculum loading failures."""


class MissingDataFileError(CurriculumLoaderError):
    """Raised when one or more required curriculum CSV files cannot be found."""

    def __init__(self, filename: str, expected_path: Path) -> None:
        self.filename = filename
        self.expected_path = expected_path
        super().__init__(
            f"Missing required data file '{filename}'. It must be placed at '{expected_path}'."
        )


class CurriculumValidationError(CurriculumLoaderError):
    """Raised when curriculum data fails pre-write validation checks."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        message = (
            f"Curriculum validation failed with {len(errors)} error(s):\n"
            + "\n".join(f"  - {err}" for err in errors)
        )
        super().__init__(message)


@dataclass
class CurriculumSummary:
    """Summary of records loaded into the curriculum database."""

    courses_count: int
    course_prerequisites_count: int
    topics_count: int
    topic_prerequisites_count: int
    dry_run: bool = False

    def format_cli_output(self) -> str:
        """Render a formatted multi-line summary table for terminal display."""
        status_line = (
            "DRY RUN (validated successfully, no changes persisted)"
            if self.dry_run
            else "Committed successfully"
        )
        return (
            "=" * 60 + "\n"
            " StudySphere Curriculum Ingestion Summary\n"
            + "=" * 60 + "\n"
            f"> Courses Processed             : {self.courses_count}\n"
            f"> Course Prerequisites Processed: {self.course_prerequisites_count}\n"
            f"> Topics Processed              : {self.topics_count}\n"
            f"> Topic Prerequisites Processed : {self.topic_prerequisites_count}\n"
            f"> Execution Status              : {status_line}\n"
            + "=" * 60
        )


def _detect_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    """Detect cycles in a directed graph using depth-first search.

    Args:
        graph: Adjacency list mapping node identifier to list of prerequisite nodes.

    Returns:
        list[str] | None: Sequence of nodes comprising the detected cycle, or None if acyclic.
    """
    state: dict[str, int] = {}  # 0 = unvisited, 1 = visiting (on stack), 2 = visited
    cycle_path: list[str] = []

    def dfs(node: str, path: list[str]) -> bool:
        state[node] = 1
        for neighbor in graph.get(node, []):
            if state.get(neighbor) == 1:
                # Cycle identified
                if neighbor in path:
                    idx = path.index(neighbor)
                    cycle_path.extend(path[idx:] + [neighbor])
                else:
                    cycle_path.extend(path + [neighbor])
                return True
            if state.get(neighbor, 0) == 0:
                if dfs(neighbor, path + [neighbor]):
                    return True
        state[node] = 2
        return False

    for node in sorted(graph.keys()):
        if state.get(node, 0) == 0:
            if dfs(node, [node]):
                return cycle_path

    return None


class CurriculumLoader:
    """Service orchestrating validation, parsing, and idempotent loading of curriculum data."""

    def __init__(self, data_dir: str | Path = "data", session: Session | None = None) -> None:
        self.data_dir: Path = Path(data_dir)
        self.session: Session = session or db.session

    def verify_files_exist(self) -> dict[str, Path]:
        """Verify that all four required curriculum CSV files exist on disk.

        Returns:
            dict[str, Path]: Map of filename to resolved absolute Path.

        Raises:
            MissingDataFileError: If any required CSV file is missing.
        """
        resolved: dict[str, Path] = {}
        for fname in REQUIRED_DATA_FILES:
            fpath = self.data_dir / fname
            if not fpath.is_file():
                raise MissingDataFileError(filename=fname, expected_path=fpath.resolve())
            resolved[fname] = fpath
        return resolved

    def read_csv(self, path: Path) -> list[dict[str, str]]:
        """Read a CSV file with utf-8-sig encoding and stripped string values.

        Args:
            path: Target file path.

        Returns:
            list[dict[str, str]]: List of row dictionaries.
        """
        with open(path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows: list[dict[str, str]] = []
            for raw_row in reader:
                cleaned: dict[str, str] = {
                    (k.strip() if k else ""): (v.strip() if v else "")
                    for k, v in raw_row.items()
                    if k is not None
                }
                rows.append(cleaned)
            return rows

    def validate(
        self,
        courses_rows: list[dict[str, str]],
        cp_rows: list[dict[str, str]],
        topics_rows: list[dict[str, str]],
        tp_rows: list[dict[str, str]],
        headers_by_file: dict[str, set[str]],
    ) -> list[str]:
        """Perform comprehensive semantic and relational validation across all curriculum rows.

        Validates:
        - Required CSV columns exist in headers.
        - Difficulty is an integer within 1-5 range.
        - No duplicate topic names within the same subject.
        - Every referenced course and topic exists.
        - No self-referencing prerequisite links.
        - No cycles in either prerequisite graph (DAG enforcement).

        Args:
            courses_rows: Rows from courses.csv.
            cp_rows: Rows from course_prerequisites.csv.
            topics_rows: Rows from topics.csv.
            tp_rows: Rows from topic_prerequisites.csv.
            headers_by_file: Set of column headers present in each file.

        Returns:
            list[str]: Accumulated validation error descriptions (empty if valid).
        """
        errors: list[str] = []

        # 1. Header validations
        for fname, req_cols in REQUIRED_COLUMNS.items():
            actual_cols = headers_by_file.get(fname, set())
            missing = set(req_cols) - actual_cols
            if missing:
                errors.append(
                    f"File '{fname}' missing required column(s): {', '.join(sorted(missing))}"
                )

        if errors:
            return errors  # Halt row-level parsing if structural columns are missing

        # 2. Courses row validation
        course_codes: set[str] = set()
        course_titles: set[str] = set()
        for i, row in enumerate(courses_rows, start=1):
            code = row.get("course_code", "")
            title = row.get("title", "")
            if not code:
                errors.append(f"courses.csv line {i}: course_code cannot be empty")
            elif code in course_codes:
                errors.append(f"courses.csv line {i}: duplicate course_code '{code}'")
            else:
                course_codes.add(code)

            if not title:
                errors.append(f"courses.csv line {i}: title cannot be empty")
            elif title in course_titles:
                errors.append(f"courses.csv line {i}: duplicate course title '{title}'")
            else:
                course_titles.add(title)

            try:
                sem = int(row.get("semester", ""))
                if sem < 1:
                    errors.append(f"courses.csv line {i}: semester must be >= 1 (got {sem})")
            except ValueError:
                errors.append(
                    f"courses.csv line {i}: invalid semester '{row.get('semester')}'"
                )

            try:
                credits = int(row.get("credit_hours", ""))
                if credits < 0:
                    errors.append(
                        f"courses.csv line {i}: credit_hours must be >= 0 (got {credits})"
                    )
            except ValueError:
                errors.append(
                    f"courses.csv line {i}: invalid credit_hours '{row.get('credit_hours')}'"
                )

        # 3. Topics row validation
        topics_by_subject: dict[str, set[str]] = {}
        all_topics: set[tuple[str, str]] = set()  # (subject, topic_name)

        for i, row in enumerate(topics_rows, start=1):
            subject = row.get("subject", "")
            topic_name = row.get("topic", "")
            diff_raw = row.get("difficulty", "")

            # Topic links to Course by matching topic's subject to course title
            if subject not in course_titles:
                errors.append(
                    f"topics.csv line {i}: subject '{subject}' does not match any Course title"
                )

            if not topic_name:
                errors.append(f"topics.csv line {i}: topic name cannot be empty")

            # Check difficulty 1-5
            try:
                diff = int(diff_raw)
                if diff < 1 or diff > 5:
                    errors.append(
                        f"topics.csv line {i} ('{topic_name}'): difficulty must be between 1 and 5 (got {diff})"
                    )
            except ValueError:
                errors.append(
                    f"topics.csv line {i} ('{topic_name}'): invalid difficulty integer '{diff_raw}'"
                )

            # Check no duplicate topic names within a subject
            subject_topics = topics_by_subject.setdefault(subject, set())
            if topic_name in subject_topics:
                errors.append(
                    f"topics.csv line {i}: duplicate topic name '{topic_name}' within subject '{subject}'"
                )
            else:
                subject_topics.add(topic_name)
                all_topics.add((subject, topic_name))

        # 4. Course prerequisites validation (existence, self-link, cycle)
        course_graph: dict[str, list[str]] = {}
        for i, row in enumerate(cp_rows, start=1):
            code = row.get("course_code", "")
            prereq = row.get("prerequisite_code", "")

            if code not in course_codes:
                errors.append(
                    f"course_prerequisites.csv line {i}: unknown course_code '{code}'"
                )
            if prereq not in course_codes:
                errors.append(
                    f"course_prerequisites.csv line {i}: unknown prerequisite_code '{prereq}'"
                )

            if code and prereq and code == prereq:
                errors.append(
                    f"course_prerequisites.csv line {i}: self-prerequisite detected on '{code}'"
                )
            elif code and prereq:
                course_graph.setdefault(code, []).append(prereq)

        cp_cycle = _detect_cycle(course_graph)
        if cp_cycle:
            cycle_str = " -> ".join(cp_cycle)
            errors.append(f"Cycle detected in course prerequisites: {cycle_str}")

        # 5. Topic prerequisites validation (existence, self-link, cycle)
        topic_graph: dict[str, list[str]] = {}
        for i, row in enumerate(tp_rows, start=1):
            subj = row.get("subject", "")
            topic = row.get("topic", "")
            p_subj = row.get("prerequisite_subject", "")
            p_topic = row.get("prerequisite_topic", "")

            target_key = (subj, topic)
            prereq_key = (p_subj, p_topic)

            if target_key not in all_topics:
                errors.append(
                    f"topic_prerequisites.csv line {i}: referenced topic '({subj}, {topic})' does not exist"
                )
            if prereq_key not in all_topics:
                errors.append(
                    f"topic_prerequisites.csv line {i}: referenced prerequisite topic '({p_subj}, {p_topic})' does not exist"
                )

            if target_key == prereq_key:
                errors.append(
                    f"topic_prerequisites.csv line {i}: self-prerequisite detected on '({subj}, {topic})'"
                )
            elif target_key in all_topics and prereq_key in all_topics:
                node_id = f"{subj}::{topic}"
                prereq_id = f"{p_subj}::{p_topic}"
                topic_graph.setdefault(node_id, []).append(prereq_id)

        tp_cycle = _detect_cycle(topic_graph)
        if tp_cycle:
            cycle_str = " -> ".join(tp_cycle)
            errors.append(f"Cycle detected in topic prerequisites: {cycle_str}")

        return errors

    def load(self, dry_run: bool = False) -> CurriculumSummary:
        """Validate, parse, and idempotently ingest all four curriculum CSV files.

        Args:
            dry_run: When True, performs complete validation and staging without committing changes.

        Returns:
            CurriculumSummary: Aggregated counts per table.

        Raises:
            MissingDataFileError: If any CSV is missing.
            CurriculumValidationError: If validation fails.
        """
        # 1. Verify all 4 files exist
        file_paths = self.verify_files_exist()

        # 2. Read headers and row data
        headers_by_file: dict[str, set[str]] = {}
        for fname, path in file_paths.items():
            with open(path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                header_row = next(reader, [])
                headers_by_file[fname] = {h.strip() for h in header_row if h}

        courses_rows = self.read_csv(file_paths["courses.csv"])
        cp_rows = self.read_csv(file_paths["course_prerequisites.csv"])
        topics_rows = self.read_csv(file_paths["topics.csv"])
        tp_rows = self.read_csv(file_paths["topic_prerequisites.csv"])

        # 3. Validate
        errors = self.validate(
            courses_rows=courses_rows,
            cp_rows=cp_rows,
            topics_rows=topics_rows,
            tp_rows=tp_rows,
            headers_by_file=headers_by_file,
        )
        if errors:
            raise CurriculumValidationError(errors)

        # 4. Ingest idempotently inside one transaction
        try:
            # Step A: Upsert Courses (natural key: code)
            existing_courses = {c.code: c for c in Course.query.all()}
            courses_by_title: dict[str, Course] = {}
            courses_by_code: dict[str, Course] = {}

            for row in courses_rows:
                code = row["course_code"]
                title = row["title"]
                sem = int(row["semester"])
                domain = row["domain"]
                credits = int(row["credit_hours"])
                contact = row["contact_hours"]
                is_elec = row.get("is_elective", "").lower() in {"1", "true", "yes", "t"}

                if code in existing_courses:
                    course = existing_courses[code]
                    course.title = title
                    course.semester = sem
                    course.domain = domain
                    course.credit_hours = credits
                    course.contact_hours = contact
                    course.is_elective = is_elec
                else:
                    course = Course(
                        code=code,
                        title=title,
                        semester=sem,
                        domain=domain,
                        credit_hours=credits,
                        contact_hours=contact,
                        is_elective=is_elec,
                    )
                    self.session.add(course)
                    existing_courses[code] = course

                courses_by_title[title] = course
                courses_by_code[code] = course

            self.session.flush()

            # Step B: Upsert Course Prerequisites (natural key: (course_id, prerequisite_course_id))
            existing_cp = {
                (cp.course_id, cp.prerequisite_course_id): cp
                for cp in CoursePrerequisite.query.all()
            }
            loaded_cp_keys: set[tuple[int, int]] = set()

            for row in cp_rows:
                c_id = courses_by_code[row["course_code"]].id
                p_id = courses_by_code[row["prerequisite_code"]].id
                pair_key = (c_id, p_id)
                loaded_cp_keys.add(pair_key)

                if pair_key not in existing_cp:
                    cp_obj = CoursePrerequisite(
                        course_id=c_id,
                        prerequisite_course_id=p_id,
                    )
                    self.session.add(cp_obj)
                    existing_cp[pair_key] = cp_obj

            self.session.flush()

            # Step C: Upsert Topics (natural key: (semester, subject, name))
            existing_topics = {
                (t.semester, t.subject, t.name): t for t in Topic.query.all()
            }
            topics_by_subj_name: dict[tuple[str, str], Topic] = {}

            for row in topics_rows:
                subj = row["subject"]
                name = row["topic"]
                sem = int(row["semester"])
                diff = int(row["difficulty"])
                desc = row.get("description") or None
                week = row.get("week") or None
                raw_tags = row.get("tags", "")
                tags_list = (
                    [t.strip() for t in raw_tags.split(";") if t.strip()]
                    if raw_tags
                    else []
                )

                course = courses_by_title[subj]
                key = (sem, subj, name)

                if key in existing_topics:
                    topic = existing_topics[key]
                    topic.course_id = course.id
                    topic.difficulty = diff
                    topic.description = desc
                    topic.tags = tags_list
                    topic.week = week
                else:
                    topic = Topic(
                        course_id=course.id,
                        semester=sem,
                        subject=subj,
                        name=name,
                        difficulty=diff,
                        description=desc,
                        tags=tags_list,
                        week=week,
                    )
                    self.session.add(topic)
                    existing_topics[key] = topic

                topics_by_subj_name[(subj, name)] = topic

            self.session.flush()

            # Step D: Upsert Topic Prerequisites (natural key: (topic_id, prerequisite_topic_id))
            existing_tp = {
                (tp.topic_id, tp.prerequisite_topic_id): tp
                for tp in Prerequisite.query.all()
            }
            loaded_tp_keys: set[tuple[int, int]] = set()

            for row in tp_rows:
                t_id = topics_by_subj_name[(row["subject"], row["topic"])].id
                p_id = topics_by_subj_name[
                    (row["prerequisite_subject"], row["prerequisite_topic"])
                ].id
                pair_key = (t_id, p_id)
                loaded_tp_keys.add(pair_key)

                if pair_key not in existing_tp:
                    tp_obj = Prerequisite(
                        topic_id=t_id,
                        prerequisite_topic_id=p_id,
                    )
                    self.session.add(tp_obj)
                    existing_tp[pair_key] = tp_obj

            self.session.flush()

            summary = CurriculumSummary(
                courses_count=len(courses_rows),
                course_prerequisites_count=len(cp_rows),
                topics_count=len(topics_rows),
                topic_prerequisites_count=len(tp_rows),
                dry_run=dry_run,
            )

            if dry_run:
                self.session.rollback()
            else:
                self.session.commit()

            return summary

        except Exception:
            self.session.rollback()
            raise


def load_curriculum(
    data_dir: str | Path = "data",
    dry_run: bool = False,
    session: Session | None = None,
) -> CurriculumSummary:
    """Convenience functional interface to instantiate and run CurriculumLoader.

    Args:
        data_dir: Directory containing curriculum CSVs.
        dry_run: If True, executes validations and staging without persistent writes.
        session: Optional SQLAlchemy session override.

    Returns:
        CurriculumSummary: Summary counts of records processed.
    """
    loader = CurriculumLoader(data_dir=data_dir, session=session)
    return loader.load(dry_run=dry_run)
