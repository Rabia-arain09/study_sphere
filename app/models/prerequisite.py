"""Prerequisite model representing directed dependencies between curriculum topics."""

from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import Integer, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db

if TYPE_CHECKING:
    from app.models.topic import Topic


class Prerequisite(db.Model):
    """Prerequisite association entity mapping curriculum concept dependencies.

    ML Pipeline Role:
        Forms the directed edges of the knowledge dependency Directed Acyclic Graph (DAG).
        When the Decision Tree classifies a target topic below proficiency ('Weak' or 'Good'),
        the Knowledge Gap Analysis service recursively traverses prerequisite relationships
        to identify foundational weak nodes, allowing the recommendation engine to suggest
        prerequisite revision prior to advancing in the target topic.
    """

    __tablename__ = "prerequisites"
    __table_args__ = (
        CheckConstraint(
            "topic_id != prerequisite_topic_id",
            name="check_no_self_prerequisite",
        ),
        UniqueConstraint(
            "topic_id",
            "prerequisite_topic_id",
            name="uq_prerequisites_topic_prerequisite",
        ),
    )

    topic_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("topics.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    prerequisite_topic_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("topics.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    # Relationships
    topic: Mapped[Topic] = relationship(
        "Topic",
        foreign_keys=[topic_id],
        back_populates="prerequisites_required",
    )
    prerequisite_topic: Mapped[Topic] = relationship(
        "Topic",
        foreign_keys=[prerequisite_topic_id],
        back_populates="prerequisite_for",
    )

    def __repr__(self) -> str:
        return (
            f"<Prerequisite topic_id={self.topic_id} "
            f"prerequisite_topic_id={self.prerequisite_topic_id}>"
        )
