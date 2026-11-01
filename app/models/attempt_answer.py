"""AttemptAnswer model representing student responses and theory self-evaluations."""

from __future__ import annotations
import enum
from typing import TYPE_CHECKING
from sqlalchemy import (
    Integer,
    Text,
    Boolean,
    String,
    ForeignKey,
    Index,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db

if TYPE_CHECKING:
    from app.models.attempt import Attempt
    from app.models.question import Question


class SelfRating(str, enum.Enum):
    """Permissible self-assessment ratings assigned by students to theory questions."""

    GOT_IT = "got_it"
    PARTLY = "partly"
    MISSED = "missed"


class AttemptAnswer(db.Model):
    """Individual question response recorded within a student quiz attempt.

    Stores the raw answer submitted by the learner, automated scoring status
    for objective question types (MCQ, TF, SHORT), and manual self-assessment
    ratings for subjective theory questions.
    """

    __tablename__ = "attempt_answers"
    __table_args__ = (
        UniqueConstraint(
            "attempt_id",
            "question_id",
            name="uq_attempt_answers_attempt_id_question_id",
        ),
        Index("ix_attempt_answers_attempt_id", "attempt_id"),
        CheckConstraint(
            "self_rating IS NULL OR self_rating IN ('got_it', 'partly', 'missed')",
            name="ck_attempt_answers_self_rating",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("attempts.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    self_rating: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Relationships
    attempt: Mapped[Attempt] = relationship("Attempt", back_populates="answers")
    question: Mapped[Question] = relationship("Question")

    def __repr__(self) -> str:
        return (
            f"<AttemptAnswer id={self.id} attempt_id={self.attempt_id} "
            f"question_id={self.question_id} is_correct={self.is_correct} "
            f"self_rating='{self.self_rating}'>"
        )
