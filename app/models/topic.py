"""Topic model representing curriculum syllabus nodes in the knowledge graph."""

from __future__ import annotations
from typing import TYPE_CHECKING, Any
from sqlalchemy import Integer, String, Text, JSON, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db

if TYPE_CHECKING:
    from app.models.prerequisite import Prerequisite
    from app.models.resource import Resource
    from app.models.question import Question
    from app.models.attempt import Attempt


class Topic(db.Model):
    """Curriculum topic entity representing syllabus nodes.

    ML Pipeline Role:
        Serves as the structural node in the curriculum knowledge graph.
        Enables 3-tier hierarchical filtering (Semester -> Subject -> Topic) for
        study recommendations. The 'difficulty' attribute provides a core feature
        for performance normalization in the Decision Tree classifier, allowing the
        model to distinguish whether low quiz scores reflect foundational student
        weakness or inherent topic complexity.
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
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[dict[str, Any] | list[str] | None] = mapped_column(
        JSON, nullable=True
    )

    # Relationships
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
            f"<Topic id={self.id} semester={self.semester} "
            f"subject='{self.subject}' name='{self.name}' difficulty={self.difficulty}>"
        )
