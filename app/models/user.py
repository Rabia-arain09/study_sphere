"""User model for authentication, cohort profiling, and learner performance tracking."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db

if TYPE_CHECKING:
    from app.models.attempt import Attempt
    from app.models.question import Question


class User(db.Model):
    """User entity representing students and instructors in StudySphere.

    ML Pipeline Role:
        Acts as the primary learning entity. Stores demographic and cohort features
        (specifically current semester enrollment), enabling the ML recommendation
        engine to partition topic discovery and baseline student performance models.
        User IDs link attempts across time to track mastery trajectory, learning velocity,
        and student-specific knowledge gap recurrence.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    attempts: Mapped[list[Attempt]] = relationship(
        "Attempt",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Attempt.created_at.desc()",
    )
    created_questions: Mapped[list[Question]] = relationship(
        "Question",
        back_populates="creator",
        foreign_keys="Question.created_by",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email='{self.email}' semester={self.semester}>"
