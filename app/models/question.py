"""Question model representing assessment items from curriculum or OCR/LLM pipelines."""

from __future__ import annotations
import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from sqlalchemy import (
    Integer,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db

if TYPE_CHECKING:
    from app.models.topic import Topic
    from app.models.user import User


class QuestionType(str, enum.Enum):
    """Enumeration of question formats supported by the evaluation engine."""

    MCQ = "mcq"
    TF = "tf"
    SHORT = "short"
    THEORY = "theory"


class QuestionSource(str, enum.Enum):
    """Source origin of the question (curriculum bank vs OCR/LLM generated)."""

    CURRICULUM = "curriculum"
    GENERATED = "generated"


class Question(db.Model):
    """Assessment item entity linked to topics and users.

    ML Pipeline Role:
        Supplies calibrated evaluation probes to assess learner proficiency.
        Questions generated via the OCR and LLM document processing pipeline are tagged
        with `source='generated'` and linked to the uploading user (`created_by`),
        providing provenance tracking and active learning validation data to fine-tune
        future automated question generators.
    """

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[QuestionType] = mapped_column(
        SQLEnum(QuestionType, native_enum=False, length=20),
        nullable=False,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSON, nullable=True
    )
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[QuestionSource] = mapped_column(
        SQLEnum(QuestionSource, native_enum=False, length=20),
        nullable=False,
        default=QuestionSource.CURRICULUM,
    )
    created_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    topic: Mapped[Topic] = relationship("Topic", back_populates="questions")
    creator: Mapped[User | None] = relationship(
        "User",
        back_populates="created_questions",
        foreign_keys=[created_by],
    )

    def __repr__(self) -> str:
        return (
            f"<Question id={self.id} topic_id={self.topic_id} "
            f"type='{self.type.value}' source='{self.source.value}'>"
        )
