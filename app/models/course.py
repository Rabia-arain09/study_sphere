"""Course and CoursePrerequisite models representing degree curriculum hierarchy and dependencies."""

from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import (
    Integer,
    String,
    Boolean,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db

if TYPE_CHECKING:
    from app.models.topic import Topic


class Course(db.Model):
    """Academic course entity representing curriculum subjects within degree programs.

    ML Pipeline Role:
        Forms the foundational tier in the hierarchical curriculum structure:
        (Semester -> Course/Subject -> Topic). Links individual syllabus concepts to
        accredited degree courses, credit weights, and academic domains (Computing Core,
        General Education, Elective), providing contextual grouping for cohort-level
        mastery analytics and domain-level knowledge gap summaries.
    """

    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("code", name="uq_courses_code"),
        UniqueConstraint("title", name="uq_courses_title"),
        Index("ix_courses_code", "code"),
        Index("ix_courses_title", "title"),
        Index("ix_courses_semester", "semester"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    domain: Mapped[str] = mapped_column(String(100), nullable=False)
    credit_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    contact_hours: Mapped[str] = mapped_column(String(20), nullable=False)
    is_elective: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Relationships
    topics: Mapped[list[Topic]] = relationship(
        "Topic",
        back_populates="course",
        cascade="all, delete-orphan",
    )
    prerequisites_required: Mapped[list[CoursePrerequisite]] = relationship(
        "CoursePrerequisite",
        foreign_keys="CoursePrerequisite.course_id",
        back_populates="course",
        cascade="all, delete-orphan",
    )
    prerequisite_for: Mapped[list[CoursePrerequisite]] = relationship(
        "CoursePrerequisite",
        foreign_keys="CoursePrerequisite.prerequisite_course_id",
        back_populates="prerequisite_course",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Course id={self.id} code='{self.code}' title='{self.title}' "
            f"semester={self.semester} credits={self.credit_hours}>"
        )


class CoursePrerequisite(db.Model):
    """Directed dependency mapping course-level prerequisites across academic semesters.

    ML Pipeline Role:
        Enforces macro-level academic constraints in the knowledge graph. When a student
        struggles across multiple topics in an advanced course, course-level prerequisite
        edges enable recursive traversal to identify whether deficient foundational courses
        require remediation before targeted topic quizzes are re-administered.
    """

    __tablename__ = "course_prerequisites"
    __table_args__ = (
        CheckConstraint(
            "course_id != prerequisite_course_id",
            name="check_no_self_course_prerequisite",
        ),
        UniqueConstraint(
            "course_id",
            "prerequisite_course_id",
            name="uq_course_prerequisites_course_prerequisite",
        ),
    )

    course_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("courses.id", ondelete="CASCADE"),
        primary_key=True,
    )
    prerequisite_course_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("courses.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Relationships
    course: Mapped[Course] = relationship(
        "Course",
        foreign_keys=[course_id],
        back_populates="prerequisites_required",
    )
    prerequisite_course: Mapped[Course] = relationship(
        "Course",
        foreign_keys=[prerequisite_course_id],
        back_populates="prerequisite_for",
    )

    def __repr__(self) -> str:
        return (
            f"<CoursePrerequisite course_id={self.course_id} "
            f"prerequisite_course_id={self.prerequisite_course_id}>"
        )
