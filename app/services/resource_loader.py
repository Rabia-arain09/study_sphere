"""Loader for curated topic resource links."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from app.extensions import db
from app.models.resource import Resource, ResourceType
from app.models.topic import Topic

REQUIRED_COLUMNS = ("subject", "topic", "title", "type", "url")
RESOURCE_FILENAME = "resources.csv"


class ResourceLoaderError(Exception):
    """Base exception for resource import failures."""


class ResourceValidationError(ResourceLoaderError):
    """Raised when a resource CSV row is invalid or references an unknown topic."""


class MissingResourceFileError(ResourceLoaderError):
    """Raised when the resource CSV file is not found."""


@dataclass
class ResourceLoadSummary:
    """Summary of resource links inserted or already present."""

    links_processed: int
    links_added: int
    links_unchanged: int
    dry_run: bool = False


class ResourceLoader:
    """Validate and idempotently load Semester 5 resource links."""

    def __init__(
        self,
        data_dir: str | Path = "data",
        session: Session | None = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.session = session or db.session

    def _read_rows(self) -> list[dict[str, str]]:
        """Read and validate the resource CSV header."""
        path = self.data_dir / RESOURCE_FILENAME
        if not path.is_file():
            raise MissingResourceFileError(
                f"Missing resource file '{path.resolve()}'."
            )

        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            missing = set(REQUIRED_COLUMNS) - set(reader.fieldnames or [])
            if missing:
                raise ResourceValidationError(
                    "resources.csv is missing required columns: "
                    + ", ".join(sorted(missing))
                )
            return [
                {
                    key: (value or "").strip()
                    for key, value in row.items()
                    if key is not None
                }
                for row in reader
            ]

    @staticmethod
    def _validate_url(url: str, line_number: int) -> None:
        """Require a fully qualified HTTP or HTTPS URL."""
        try:
            parsed = urlsplit(url)
            valid = (
                parsed.scheme.lower() in {"http", "https"}
                and bool(parsed.hostname)
            )
        except ValueError:
            valid = False
        if not valid:
            raise ResourceValidationError(
                f"resources.csv line {line_number}: URL must use HTTP or HTTPS."
            )

    def load(self, dry_run: bool = False) -> ResourceLoadSummary:
        """Insert missing Semester 5 links without changing unrelated records."""
        rows = self._read_rows()
        resolved_rows: list[tuple[Topic, dict[str, str]]] = []
        seen_rows: set[tuple[str, str, str, str, str]] = set()

        for line_number, row in enumerate(rows, start=2):
            subject = row["subject"]
            topic_name = row["topic"]
            title = row["title"]
            resource_type = row["type"].lower()
            url = row["url"]
            if not all((subject, topic_name, title, resource_type, url)):
                raise ResourceValidationError(
                    f"resources.csv line {line_number}: all columns are required."
                )
            if resource_type != ResourceType.LINK.value:
                raise ResourceValidationError(
                    f"resources.csv line {line_number}: type must be 'link'."
                )
            self._validate_url(url, line_number)

            key = (subject, topic_name, title, resource_type, url)
            if key in seen_rows:
                continue
            seen_rows.add(key)

            topic = self.session.query(Topic).filter_by(
                semester=5,
                subject=subject,
                name=topic_name,
            ).one_or_none()
            if topic is None:
                raise ResourceValidationError(
                    f"resources.csv line {line_number}: unknown Semester 5 topic "
                    f"'{subject} / {topic_name}'."
                )
            resolved_rows.append((topic, row))

        existing_keys = {
            (
                topic.subject,
                topic.name,
                resource.title,
                resource.type.value,
                resource.url,
            )
            for resource, topic in self.session.query(Resource, Topic)
            .join(Topic, Resource.topic_id == Topic.id)
            .filter(Topic.semester == 5)
            .all()
        }

        added = 0
        unchanged = 0
        try:
            for topic, row in resolved_rows:
                key = (
                    topic.subject,
                    topic.name,
                    row["title"],
                    row["type"].lower(),
                    row["url"],
                )
                if key in existing_keys:
                    unchanged += 1
                    continue
                self.session.add(
                    Resource(
                        topic_id=topic.id,
                        title=row["title"],
                        type=ResourceType.LINK,
                        url=row["url"],
                    )
                )
                existing_keys.add(key)
                added += 1

            if dry_run:
                self.session.rollback()
            else:
                self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        return ResourceLoadSummary(
            links_processed=len(resolved_rows),
            links_added=added,
            links_unchanged=unchanged,
            dry_run=dry_run,
        )


def load_resources(
    data_dir: str | Path = "data",
    dry_run: bool = False,
    session: Session | None = None,
) -> ResourceLoadSummary:
    """Convenience function to load the configured resource CSV."""
    return ResourceLoader(data_dir=data_dir, session=session).load(dry_run=dry_run)
