"""Resource model representing study material attached to curriculum topics."""

from __future__ import annotations
import enum
from typing import TYPE_CHECKING
from sqlalchemy import Integer, String, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db

if TYPE_CHECKING:
    from app.models.topic import Topic


class ResourceType(str, enum.Enum):
    """Enumeration of allowed learning resource media types."""

    NOTE = "note"
    IMAGE = "image"
    DIAGRAM = "diagram"
    LINK = "link"


class Resource(db.Model):
    """Learning resource entity (notes, diagrams, references) mapped to a topic.

    ML Pipeline Role:
        Acts as the delivery payload in the adaptive remediation engine.
        Once the Decision Tree flags a student's topic mastery as 'Weak' or 'Needs Revision',
        the recommendation pipeline surfaces prioritized resources matching the topic
        and its deficient prerequisites, guiding students directly to targeted learning aids.
    """

    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[ResourceType] = mapped_column(
        SQLEnum(ResourceType, native_enum=False, length=20),
        nullable=False,
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)

    # Relationships
    topic: Mapped[Topic] = relationship("Topic", back_populates="resources")

    def __repr__(self) -> str:
        return (
            f"<Resource id={self.id} topic_id={self.topic_id} "
            f"type='{self.type.value}' title='{self.title}'>"
        )
