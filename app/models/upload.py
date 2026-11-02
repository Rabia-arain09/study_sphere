"""Upload model storing user-uploaded study materials, summaries, and generated quizzes."""

from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any
from sqlalchemy import Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db

if TYPE_CHECKING:
    from app.models.user import User


class UploadSourceType(str, Enum):
    """Enumeration of accepted upload source channels."""

    TEXT = "text"
    IMAGE = "image"
    URL = "url"


class Upload(db.Model):
    """Upload entity holding extracted text, LLM summaries, key terms, and quizzes.

    Pipeline Role:
        Captures ad-hoc learner study material (pasted text, lecture slide images,
        educational URLs) and stores structured LLM artifacts (concise bullet summary,
        simplified plain-language explanation, key glossary terms, and adaptive quiz
        questions) along with assessment performance metrics.
    """

    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    simple_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    key_terms: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=False)
    questions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship to user
    user: Mapped[User] = relationship("User", back_populates="uploads")

    def __repr__(self) -> str:
        """Format debug string for upload entity."""
        return f"<Upload id={self.id} user_id={self.user_id} title='{self.title[:30]}' source={self.source_type}>"
