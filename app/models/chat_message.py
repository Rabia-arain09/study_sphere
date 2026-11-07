"""Persisted, user-scoped study chat messages."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db

if TYPE_CHECKING:
    from app.models.topic import Topic
    from app.models.upload import Upload
    from app.models.user import User


class ChatMessage(db.Model):
    """A user or assistant message scoped to one topic or uploaded material."""

    __tablename__ = "chat_message"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant')",
            name="role",
        ),
        CheckConstraint(
            "(topic_id IS NOT NULL AND upload_id IS NULL) OR "
            "(topic_id IS NULL AND upload_id IS NOT NULL)",
            name="single_context",
        ),
        Index(
            "ix_chat_message_user_topic_created",
            "user_id",
            "topic_id",
            "created_at",
        ),
        Index(
            "ix_chat_message_user_upload_created",
            "user_id",
            "upload_id",
            "created_at",
        ),
        Index(
            "ix_chat_message_user_role_created",
            "user_id",
            "role",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic_id: Mapped[int | None] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=True,
    )
    upload_id: Mapped[int | None] = mapped_column(
        ForeignKey("uploads.id", ondelete="CASCADE"),
        nullable=True,
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped[User] = relationship("User")
    topic: Mapped[Topic | None] = relationship("Topic")
    upload: Mapped[Upload | None] = relationship("Upload")

    def __repr__(self) -> str:
        """Return a concise representation without exposing message contents."""
        return (
            f"<ChatMessage id={self.id} user_id={self.user_id} "
            f"role='{self.role}'>"
        )
