"""Attempt model representing student quiz sessions and ML classification inputs/outputs."""

from __future__ import annotations
import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import (
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db

if TYPE_CHECKING:
    from app.models.topic import Topic
    from app.models.user import User


class MasteryLabel(str, enum.Enum):
    """Classification labels assigned to topic mastery by the Decision Tree classifier."""

    STRONG = "Strong"
    NEEDS_REVISION = "Needs Revision"
    WEAK = "Weak"


class Attempt(db.Model):
    """Quiz attempt record logging learner performance on a specific topic.

    ML Pipeline Role:
        Primary dataset table for the Decision Tree classification model.
        Numerical columns (score, total_questions, wrong_count, attempt_number) serve
        as raw input features for both real-time model inference and supervised offline
        re-training. The 'label' column stores the resulting classification
        (Strong / Needs Revision / Weak), which feeds directly into the knowledge gap
        graph traversal algorithm and adaptive dashboard analytics.
    """

    __tablename__ = "attempts"
    __table_args__ = (
        Index("ix_attempts_user_id_topic_id", "user_id", "topic_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[MasteryLabel | None] = mapped_column(
        SQLEnum(MasteryLabel, native_enum=False, length=30),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="attempts")
    topic: Mapped[Topic] = relationship("Topic", back_populates="attempts")

    def __repr__(self) -> str:
        return (
            f"<Attempt id={self.id} user_id={self.user_id} topic_id={self.topic_id} "
            f"score={self.score} label={self.label.value if self.label else None}>"
        )
