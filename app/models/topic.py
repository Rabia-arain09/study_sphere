"""Topic model representing curriculum syllabus nodes in the knowledge graph."""

from __future__ import annotations
import enum
from typing import TYPE_CHECKING, Any
from sqlalchemy import (
    Integer,
    String,
    Text,
    Boolean,
    JSON,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.prerequisite import Prerequisite
    from app.models.resource import Resource
    from app.models.question import Question
    from app.models.attempt import Attempt


class ContentSource(str, enum.Enum):
    """Enumeration of study note content authoring sources."""

    LECTURE = "lecture"
    AI_GENERATED = "ai_generated"


class Topic(db.Model):
    """Curriculum topic entity representing syllabus nodes.

    ML Pipeline Role:
        Serves as the structural node in the curriculum knowledge graph.
        Enables hierarchical filtering (Semester -> Course/Subject -> Topic) for
        study recommendations. The 'difficulty' attribute provides a core feature
        for performance normalization in the Decision Tree classifier, allowing the
        model to distinguish whether low quiz scores reflect foundational student
        weakness or inherent topic complexity. The Markdown study notes stored in
        'content' provide curriculum ground-truth for automated question generation
        and targeted student remediation.
    """

    __tablename__ = "topics"
    __table_args__ = (
        CheckConstraint(
            "difficulty >= 1 AND difficulty <= 5",
            name="check_topic_difficulty_range",
        ),
        UniqueConstraint(
            "semester",
            "subject",
            "name",
            name="uq_topic_semester_subject_name",
        ),
        Index("ix_topics_semester", "semester"),
        Index("ix_topics_subject", "subject"),
        Index("ix_topics_course_id", "course_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[dict[str, Any] | list[str] | None] = mapped_column(
        JSON, nullable=True
    )
    week: Mapped[str | None] = mapped_column(String(50), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_source: Mapped[ContentSource | None] = mapped_column(
        SQLEnum(
            ContentSource,
            name="contentsource",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=False,
            length=20,
        ),
        nullable=True,
    )
    content_reviewed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Relationships
    course: Mapped[Course] = relationship("Course", back_populates="topics")
    prerequisites_required: Mapped[list[Prerequisite]] = relationship(
        "Prerequisite",
        foreign_keys="Prerequisite.topic_id",
        back_populates="topic",
        cascade="all, delete-orphan",
    )
    prerequisite_for: Mapped[list[Prerequisite]] = relationship(
        "Prerequisite",
        foreign_keys="Prerequisite.prerequisite_topic_id",
        back_populates="prerequisite_topic",
        cascade="all, delete-orphan",
    )
    resources: Mapped[list[Resource]] = relationship(
        "Resource",
        back_populates="topic",
        cascade="all, delete-orphan",
    )
    questions: Mapped[list[Question]] = relationship(
        "Question",
        back_populates="topic",
        cascade="all, delete-orphan",
    )
    attempts: Mapped[list[Attempt]] = relationship(
        "Attempt",
        back_populates="topic",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Topic id={self.id} course_id={self.course_id} semester={self.semester} "
            f"subject='{self.subject}' name='{self.name}' difficulty={self.difficulty}>"
        )
