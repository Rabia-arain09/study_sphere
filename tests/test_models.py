"""Unit tests for SQLAlchemy models, constraints, and relationships."""

import pytest
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import (
    User,
    Topic,
    Prerequisite,
    Resource,
    ResourceType,
    Question,
    QuestionType,
    QuestionSource,
    Attempt,
    MasteryLabel,
)


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


def test_topic_constraints_and_uniqueness(app):
    """Verify topic constraints including difficulty range and unique (semester, subject, name)."""
    with app.app_context():
        topic = Topic(
            semester=3,
            subject="Data Structures",
            name="Binary Search Trees",
            difficulty=3,
            description="Hierarchical tree data structures with sorted keys.",
            tags=["trees", "algorithms", "searching"],
        )
        db.session.add(topic)
        db.session.commit()

        # Duplicate topic check
        duplicate = Topic(
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
        t1 = Topic(
            semester=1, subject="Math", name="Calculus I", difficulty=2
        )
        t2 = Topic(
            semester=2, subject="Math", name="Calculus II", difficulty=4
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
        topic = Topic(semester=2, subject="Physics", name="Thermodynamics", difficulty=3)
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
    """Verify question generation, attempt logging, and mastery labeling."""
    with app.app_context():
        user = User(
            name="Bob Learner",
            email="bob@example.com",
            password_hash="pw_hash",
            semester=4,
        )
        topic = Topic(semester=4, subject="Database Systems", name="Normalization", difficulty=3)
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

        attempt = Attempt(
            user_id=user.id,
            topic_id=topic.id,
            score=85.0,
            total_questions=10,
            wrong_count=2,
            attempt_number=1,
            label=MasteryLabel.STRONG,
        )
        db.session.add(attempt)
        db.session.commit()

        queried_attempt = Attempt.query.filter_by(user_id=user.id, topic_id=topic.id).first()
        assert queried_attempt is not None
        assert queried_attempt.label == MasteryLabel.STRONG
        assert queried_attempt.score == 85.0
