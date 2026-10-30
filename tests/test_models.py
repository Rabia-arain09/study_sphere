"""Unit tests for SQLAlchemy models, constraints, and relationships."""

import pytest
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import (
    User,
    Course,
    CoursePrerequisite,
    Topic,
    ContentSource,
    Prerequisite,
    Resource,
    ResourceType,
    Question,
    QuestionType,
    QuestionSource,
    Attempt,
    MasteryLabel,
)


def _make_course(
    code: str = "CS101",
    title: str = "Intro to CS",
    semester: int = 1,
    domain: str = "Computing Core",
    credit_hours: int = 3,
    contact_hours: str = "3-0",
    is_elective: bool = False,
) -> Course:
    """Helper to instantiate and persist a Course for testing."""
    course = Course(
        code=code,
        title=title,
        semester=semester,
        domain=domain,
        credit_hours=credit_hours,
        contact_hours=contact_hours,
        is_elective=is_elective,
    )
    db.session.add(course)
    db.session.commit()
    return course


def test_user_creation(app):
    """Verify user creation with constraints and string representation."""
    with app.app_context():
        user = User(
            name="Alice Student",
            email="alice@example.com",
            password_hash="hashed_pw_123",
            semester=3,
        )
        db.session.add(user)
        db.session.commit()

        queried = User.query.filter_by(email="alice@example.com").first()
        assert queried is not None
        assert queried.name == "Alice Student"
        assert queried.semester == 3
        assert "alice@example.com" in repr(queried)


def test_course_creation_and_prerequisites(app):
    """Verify Course model constraints, uniqueness, and CoursePrerequisite mappings."""
    with app.app_context():
        c1 = _make_course(code="CS101", title="Programming I", semester=1)
        c2 = _make_course(code="CS102", title="Programming II", semester=2)

        # Unique code constraint
        dup_code = Course(
            code="CS101",
            title="Different Title",
            semester=1,
            domain="Computing Core",
            credit_hours=3,
            contact_hours="3-0",
        )
        db.session.add(dup_code)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        # Valid course prerequisite
        prereq = CoursePrerequisite(
            course_id=c2.id,
            prerequisite_course_id=c1.id,
        )
        db.session.add(prereq)
        db.session.commit()

        assert len(c2.prerequisites_required) == 1
        assert c2.prerequisites_required[0].prerequisite_course.code == "CS101"

        # Invalid self-prerequisite check
        self_prereq = CoursePrerequisite(
            course_id=c1.id,
            prerequisite_course_id=c1.id,
        )
        db.session.add(self_prereq)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_topic_constraints_and_uniqueness(app):
    """Verify topic constraints including difficulty range and unique (semester, subject, name)."""
    with app.app_context():
        course = _make_course(code="CS201", title="Data Structures", semester=3)

        topic = Topic(
            course_id=course.id,
            semester=3,
            subject="Data Structures",
            name="Binary Search Trees",
            difficulty=3,
            description="Hierarchical tree data structures with sorted keys.",
            tags=["trees", "algorithms", "searching"],
            week="4",
            content="# Binary Search Trees\nNotes on BST.",
            content_source=ContentSource.LECTURE,
            content_reviewed=True,
        )
        db.session.add(topic)
        db.session.commit()

        assert topic.week == "4"
        assert topic.content_reviewed is True
        assert topic.content_source == ContentSource.LECTURE
        assert topic.course.code == "CS201"

        # Duplicate topic check (semester, subject, name)
        duplicate = Topic(
            course_id=course.id,
            semester=3,
            subject="Data Structures",
            name="Binary Search Trees",
            difficulty=2,
        )
        db.session.add(duplicate)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_prerequisite_and_no_self_dependency(app):
    """Verify prerequisite mapping and no self-dependency check constraint."""
    with app.app_context():
        course = _make_course(code="MT101", title="Math", semester=1)
        t1 = Topic(
            course_id=course.id,
            semester=1,
            subject="Math",
            name="Calculus I",
            difficulty=2,
        )
        t2 = Topic(
            course_id=course.id,
            semester=2,
            subject="Math",
            name="Calculus II",
            difficulty=4,
        )
        db.session.add_all([t1, t2])
        db.session.commit()

        # Valid prerequisite: Calculus II requires Calculus I
        prereq = Prerequisite(
            topic_id=t2.id,
            prerequisite_topic_id=t1.id,
        )
        db.session.add(prereq)
        db.session.commit()

        assert len(t2.prerequisites_required) == 1
        assert t2.prerequisites_required[0].prerequisite_topic.name == "Calculus I"

        # Invalid self-prerequisite check
        self_prereq = Prerequisite(topic_id=t1.id, prerequisite_topic_id=t1.id)
        db.session.add(self_prereq)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_resource_creation(app):
    """Verify resource creation attached to a topic."""
    with app.app_context():
        course = _make_course(code="PHY101", title="Physics", semester=2)
        topic = Topic(
            course_id=course.id,
            semester=2,
            subject="Physics",
            name="Thermodynamics",
            difficulty=3,
        )
        db.session.add(topic)
        db.session.commit()

        res = Resource(
            topic_id=topic.id,
            title="Laws of Thermodynamics Cheatsheet",
            type=ResourceType.NOTE,
            url="https://example.com/thermo-cheatsheet.pdf",
        )
        db.session.add(res)
        db.session.commit()

        assert len(topic.resources) == 1
        assert topic.resources[0].type == ResourceType.NOTE


def test_question_and_attempt_pipeline(app):
    """Verify question generation, attempt logging, and 4-tier mastery labeling."""
    with app.app_context():
        user = User(
            name="Bob Learner",
            email="bob@example.com",
            password_hash="pw_hash",
            semester=4,
        )
        course = _make_course(code="CS301", title="Database Systems", semester=4)
        topic = Topic(
            course_id=course.id,
            semester=4,
            subject="Database Systems",
            name="Normalization",
            difficulty=3,
        )
        db.session.add_all([user, topic])
        db.session.commit()

        question = Question(
            topic_id=topic.id,
            type=QuestionType.MCQ,
            question_text="What does 3NF prevent?",
            options={"A": "Transitive dependencies", "B": "Partial dependencies"},
            correct_answer="A",
            source=QuestionSource.GENERATED,
            created_by=user.id,
        )
        db.session.add(question)
        db.session.commit()

        # Test 4-tier MasteryLabel values
        labels = [
            MasteryLabel.WEAK,
            MasteryLabel.GOOD,
            MasteryLabel.BETTER,
            MasteryLabel.EXCELLENT,
        ]
        assert [l.value for l in labels] == ["Weak", "Good", "Better", "Excellent"]

        attempt = Attempt(
            user_id=user.id,
            topic_id=topic.id,
            score=85.0,
            total_questions=10,
            wrong_count=2,
            attempt_number=1,
            label=MasteryLabel.EXCELLENT,
        )
        db.session.add(attempt)
        db.session.commit()

        queried_attempt = Attempt.query.filter_by(
            user_id=user.id, topic_id=topic.id
        ).first()
        assert queried_attempt is not None
        assert queried_attempt.label == MasteryLabel.EXCELLENT
        assert queried_attempt.label.value == "Excellent"
        assert queried_attempt.score == 85.0
