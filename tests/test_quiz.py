"""Unit and integration tests for the StudySphere quiz assessment engine and question loader."""

from __future__ import annotations
from pathlib import Path
import pytest
from flask import Flask
from flask.testing import FlaskClient
from app.extensions import db
from app.models.user import User
from app.models.course import Course
from app.models.topic import Topic
from app.models.question import Question, QuestionType, QuestionSource
from app.models.attempt import Attempt
from app.services.quiz_engine import (
    evaluate_single_answer,
    score_quiz,
    get_topic_quiz_questions,
    normalize_short_answer,
)
from app.services.question_loader import (
    QuestionLoader,
    QuestionsValidationError,
    MissingQuestionsFileError,
)


@pytest.fixture
def quiz_setup(app: Flask, test_user: User) -> dict[str, int]:
    """Populate test database with a course, a topic, and calibrated questions of all four types."""
    with app.app_context():
        course = Course(
            code="CS310",
            title="Machine Learning",
            semester=5,
            domain="Computer Science",
            credit_hours=3,
            contact_hours="3-0-3",
        )
        db.session.add(course)
        db.session.commit()

        topic = Topic(
            course_id=course.id,
            semester=5,
            subject="Machine Learning",
            name="Introduction to Machine Learning",
            difficulty=2,
            content="# Intro to ML\nNotes content...",
        )
        db.session.add(topic)
        db.session.commit()

        q_mcq = Question(
            topic_id=topic.id,
            type=QuestionType.MCQ,
            question_text="Which of the following is a supervised learning task?",
            options={
                "A": "Predicting house prices from features",
                "B": "Clustering customers by activity",
                "C": "Discovering latent topics in news",
                "D": "Playing chess via game rewards",
            },
            correct_answer="A",
            source=QuestionSource.CURRICULUM,
        )

        q_tf = Question(
            topic_id=topic.id,
            type=QuestionType.TF,
            question_text="Reinforcement learning relies on reward signals from the environment.",
            options={"A": "True", "B": "False"},
            correct_answer="True",
            source=QuestionSource.CURRICULUM,
        )

        q_short = Question(
            topic_id=topic.id,
            type=QuestionType.SHORT,
            question_text="What learning paradigm uses ground-truth labels during training?",
            options=None,
            correct_answer="supervised|supervised learning",
            source=QuestionSource.CURRICULUM,
        )

        q_theory = Question(
            topic_id=topic.id,
            type=QuestionType.THEORY,
            question_text="Explain the core difference between classification and regression.",
            options=None,
            correct_answer="Classification predicts discrete classes, whereas regression predicts continuous numeric values.",
            source=QuestionSource.CURRICULUM,
        )

        db.session.add_all([q_mcq, q_tf, q_short, q_theory])
        db.session.commit()

        return {
            "course_id": course.id,
            "topic_id": topic.id,
            "q_mcq_id": q_mcq.id,
            "q_tf_id": q_tf.id,
            "q_short_id": q_short.id,
            "q_theory_id": q_theory.id,
        }


# ==============================================================================
# 1. Scoring Logic Unit Tests for Each Question Type
# ==============================================================================

def test_mcq_scoring_evaluates_keys_and_labels(app: Flask, quiz_setup: dict):
    """Verify MCQ scoring correctly checks option keys case-insensitively and option labels."""
    with app.app_context():
        q_mcq = db.session.get(Question, quiz_setup["q_mcq_id"])
        assert q_mcq is not None

        # Correct option key
        assert evaluate_single_answer(q_mcq, "A") is True
        assert evaluate_single_answer(q_mcq, "a") is True
        assert evaluate_single_answer(q_mcq, " A ") is True

        # Incorrect option key
        assert evaluate_single_answer(q_mcq, "B") is False
        assert evaluate_single_answer(q_mcq, "C") is False

        # Option text match
        assert (
            evaluate_single_answer(q_mcq, "Predicting house prices from features")
            is True
        )
        assert evaluate_single_answer(q_mcq, "Clustering customers by activity") is False


def test_tf_scoring_evaluates_case_insensitively(app: Flask, quiz_setup: dict):
    """Verify True/False scoring handles case-insensitivity and whitespace."""
    with app.app_context():
        q_tf = db.session.get(Question, quiz_setup["q_tf_id"])
        assert q_tf is not None

        assert evaluate_single_answer(q_tf, "True") is True
        assert evaluate_single_answer(q_tf, "true") is True
        assert evaluate_single_answer(q_tf, " TRUE ") is True

        assert evaluate_single_answer(q_tf, "False") is False
        assert evaluate_single_answer(q_tf, "false") is False
        assert evaluate_single_answer(q_tf, "") is False


def test_short_scoring_evaluates_multiple_accepted_answers(
    app: Flask, quiz_setup: dict
):
    """Verify short answer scoring handles case-insensitivity and '|'-delimited accepted answers."""
    with app.app_context():
        q_short = db.session.get(Question, quiz_setup["q_short_id"])
        assert q_short is not None

        # Matches first accepted answer
        assert evaluate_single_answer(q_short, "supervised") is True
        assert evaluate_single_answer(q_short, "SUPERVISED") is True
        assert evaluate_single_answer(q_short, "  supervised  ") is True

        # Matches second accepted answer
        assert evaluate_single_answer(q_short, "supervised learning") is True
        assert evaluate_single_answer(q_short, "Supervised Learning") is True

        # Wrong answer
        assert evaluate_single_answer(q_short, "unsupervised") is False
        assert evaluate_single_answer(q_short, "reinforcement") is False
        assert evaluate_single_answer(q_short, "") is False


def test_normalize_short_answer_rules():
    """Verify normalize_short_answer applies trimming, lowercase, hyphens, punctuation, and articles."""
    # Lowercase & trimming & collapsing spaces
    assert normalize_short_answer("  Left   Recursion  ") == "left recursion"
    # Hyphens and underscores to spaces
    assert normalize_short_answer("left-recursive") == "left recursive"
    assert normalize_short_answer("left_recursion") == "left recursion"
    # Punctuation stripping
    assert normalize_short_answer("left recursive!") == "left recursive"
    assert normalize_short_answer('"left recursion"') == "left recursion"
    # Leading articles (a, an, the)
    assert normalize_short_answer("the left recursion") == "left recursion"
    assert normalize_short_answer("a binary tree") == "binary tree"
    assert normalize_short_answer("an operating system") == "operating system"
    # Single-word articles and pure symbols are preserved safely
    assert normalize_short_answer("the") == "the"
    assert normalize_short_answer("a") == "a"
    assert normalize_short_answer("$") == "$"
    assert normalize_short_answer("") == ""


def test_short_scoring_left_recursion_tolerant_matching(app: Flask):
    """Verify that 'left recursive', 'Left-Recursion', and ' the left recursion ' evaluate as correct."""
    with app.app_context():
        q = Question(
            type=QuestionType.SHORT,
            question_text="Which type of recursion enforces left associativity?",
            correct_answer="left recursion|left-recursive",
        )

        # Requirement 5: 'left recursive', 'Left-Recursion', ' the left recursion ' are correct
        assert evaluate_single_answer(q, "left recursive") is True
        assert evaluate_single_answer(q, "Left-Recursion") is True
        assert evaluate_single_answer(q, " the left recursion ") is True

        # Equivalent variants and forms
        assert evaluate_single_answer(q, "LEFT RECURSION") is True
        assert evaluate_single_answer(q, "left-recursive") is True
        assert evaluate_single_answer(q, "a left recursion") is True

        # Requirement 5: wrong answer such as 'right recursion' is still wrong
        assert evaluate_single_answer(q, "right recursion") is False
        assert evaluate_single_answer(q, "Right-Recursive") is False
        assert evaluate_single_answer(q, "recursion") is False
        assert evaluate_single_answer(q, "left") is False
        assert evaluate_single_answer(q, "") is False


def test_theory_question_excluded_from_score_and_totals(
    app: Flask, quiz_setup: dict
):
    """Verify theory questions return None for is_correct and are excluded from score/totals."""
    with app.app_context():
        topic_id = quiz_setup["topic_id"]
        questions = Question.query.filter_by(topic_id=topic_id).all()
        q_theory = db.session.get(Question, quiz_setup["q_theory_id"])
        assert q_theory is not None

        # Single answer evaluation returns None
        assert (
            evaluate_single_answer(
                q_theory,
                "Classification is discrete while regression is continuous.",
            )
            is None
        )

        # In aggregate quiz scoring: 3 scorable questions + 1 theory = total_questions == 3
        answers = {
            q.id: "A" if q.type == QuestionType.MCQ else "True"
            for q in questions
        }
        # Mark short as correct
        answers[quiz_setup["q_short_id"]] = "supervised"
        answers[quiz_setup["q_theory_id"]] = "My long explanation..."

        result = score_quiz(questions, answers)
        assert result.total_questions == 3  # Theory excluded
        assert result.score == 3.0
        assert result.wrong_count == 0
        assert result.percentage == 100.0

        # Theory detail retains reference answer
        theory_detail = [d for d in result.details if d.question_id == q_theory.id][0]
        assert theory_detail.is_correct is None
        assert (
            "Classification predicts discrete classes"
            in theory_detail.correct_answer
        )


# ==============================================================================
# 2. Security and Anti-Tampering Tests
# ==============================================================================

def test_no_correct_answer_leakage_in_quiz_html(
    auth_client: FlaskClient, quiz_setup: dict
):
    """Verify that correct answers are never rendered in the GET /quiz/topic/<topic_id> HTML."""
    topic_id = quiz_setup["topic_id"]
    resp = auth_client.get(f"/quiz/topic/{topic_id}")
    assert resp.status_code == 200

    html = resp.data.decode("utf-8")
    assert "correct_answer" not in html.lower()
    assert "supervised|supervised learning" not in html
    assert "Classification predicts discrete classes, whereas regression" not in html


def test_tampered_question_ids_are_ignored(
    auth_client: FlaskClient, quiz_setup: dict, app: Flask
):
    """Verify that submitting unrecognized or out-of-session question IDs is ignored."""
    topic_id = quiz_setup["topic_id"]

    # 1. Start quiz to establish valid session
    get_resp = auth_client.get(f"/quiz/topic/{topic_id}")
    assert get_resp.status_code == 200

    # 2. Submit form with legitimate answers plus a rogue tampered ID (e.g., 999999)
    with app.app_context():
        questions = Question.query.filter_by(topic_id=topic_id).all()
        post_data = {f"question_{q.id}": "A" for q in questions}
        post_data["question_999999"] = "rogue_injected_answer"

    post_resp = auth_client.post(
        f"/quiz/topic/{topic_id}/submit",
        data=post_data,
        follow_redirects=True,
    )
    assert post_resp.status_code == 200

    # Verify attempt was recorded without error and total_questions is strictly 3 (4 total minus 1 theory)
    with app.app_context():
        attempt = Attempt.query.filter_by(topic_id=topic_id).order_by(Attempt.id.desc()).first()
        assert attempt is not None
        assert attempt.total_questions == 3


def test_answer_length_is_safely_limited(
    auth_client: FlaskClient, quiz_setup: dict, app: Flask
):
    """Verify submitted answers exceeding length bounds are truncated safely without error."""
    topic_id = quiz_setup["topic_id"]
    auth_client.get(f"/quiz/topic/{topic_id}")

    with app.app_context():
        questions = Question.query.filter_by(topic_id=topic_id).all()
        post_data = {f"question_{q.id}": "x" * 10000 for q in questions}

    post_resp = auth_client.post(
        f"/quiz/topic/{topic_id}/submit",
        data=post_data,
        follow_redirects=True,
    )
    assert post_resp.status_code == 200


# ==============================================================================
# 3. Quiz Workflow and Attempt Progression Tests
# ==============================================================================

def test_attempt_number_increments_for_same_user_and_topic(
    auth_client: FlaskClient, quiz_setup: dict, app: Flask
):
    """Verify attempt_number monotonically increments with successive attempts by same user."""
    topic_id = quiz_setup["topic_id"]

    for expected_attempt_num in (1, 2, 3):
        # GET quiz page
        auth_client.get(f"/quiz/topic/{topic_id}")

        with app.app_context():
            questions = Question.query.filter_by(topic_id=topic_id).all()
            post_data = {f"question_{q.id}": "A" for q in questions}

        resp = auth_client.post(
            f"/quiz/topic/{topic_id}/submit",
            data=post_data,
            follow_redirects=True,
        )
        assert resp.status_code == 200

        with app.app_context():
            latest = (
                Attempt.query.filter_by(topic_id=topic_id)
                .order_by(Attempt.id.desc())
                .first()
            )
            assert latest is not None
            assert latest.attempt_number == expected_attempt_num
            # Label must remain None in Phase 4 (Decision Tree comes in Phase 5)
            assert latest.label is None


def test_empty_topic_shows_friendly_coming_soon_page(
    auth_client: FlaskClient, app: Flask
):
    """Verify that a topic without questions shows a friendly 'Quiz coming soon' page (HTTP 200)."""
    with app.app_context():
        course = Course(
            code="CS999",
            title="Empty Course",
            semester=1,
            domain="General",
            credit_hours=3,
            contact_hours="3-0-3",
        )
        db.session.add(course)
        db.session.commit()

        empty_topic = Topic(
            course_id=course.id,
            semester=1,
            subject="Empty Course",
            name="Unpopulated Topic",
            difficulty=1,
        )
        db.session.add(empty_topic)
        db.session.commit()
        empty_topic_id = empty_topic.id

    resp = auth_client.get(f"/quiz/topic/{empty_topic_id}")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Quiz Coming Soon" in html
    assert "Return to Unpopulated Topic Notes" in html


def test_nonexistent_topic_returns_404(auth_client: FlaskClient):
    """Verify that querying a nonexistent topic returns 404."""
    resp = auth_client.get("/quiz/topic/999999")
    assert resp.status_code == 404

    resp_post = auth_client.post("/quiz/topic/999999/submit", data={})
    assert resp_post.status_code == 404


# ==============================================================================
# 4. Access Control and Ownership Tests
# ==============================================================================

def test_quiz_routes_require_login(client: FlaskClient, quiz_setup: dict):
    """Verify unauthenticated requests to quiz routes redirect to login."""
    topic_id = quiz_setup["topic_id"]

    # GET quiz
    r1 = client.get(f"/quiz/topic/{topic_id}")
    assert r1.status_code == 302
    assert "/auth/login" in r1.headers["Location"]

    # POST submit
    r2 = client.post(f"/quiz/topic/{topic_id}/submit", data={})
    assert r2.status_code == 302
    assert "/auth/login" in r2.headers["Location"]

    # GET attempt
    r3 = client.get("/quiz/attempt/1")
    assert r3.status_code == 302
    assert "/auth/login" in r3.headers["Location"]


def test_attempt_result_page_is_owner_only(
    app: Flask, client: FlaskClient, quiz_setup: dict, test_user: User
):
    """Verify that an attempt result page is strictly 404 for any user other than the owner."""
    topic_id = quiz_setup["topic_id"]

    # 1. Create Attempt belonging to test_user
    with app.app_context():
        attempt = Attempt(
            user_id=test_user.id,
            topic_id=topic_id,
            score=2.0,
            total_questions=3,
            wrong_count=1,
            attempt_number=1,
            label=None,
        )
        db.session.add(attempt)
        db.session.commit()
        attempt_id = attempt.id
        attempt_num = attempt.attempt_number

        # 2. Create a second user (Eve)
        eve = User(
            name="Eve Intruder",
            email="eve@example.com",
            semester=5,
        )
        eve.set_password("EveSecure123")
        db.session.add(eve)
        db.session.commit()

    # Log in as Eve
    client.post(
        "/auth/login",
        data={"email": "eve@example.com", "password": "EveSecure123"},
        follow_redirects=True,
    )

    # Eve tries to access test_user's attempt result -> must be 404
    resp_eve = client.get(f"/quiz/attempt/{attempt_id}")
    assert resp_eve.status_code == 404

    # Log out Eve, log in as test_user (owner) -> must be 200
    client.get("/auth/logout", follow_redirects=True)
    client.post(
        "/auth/login",
        data={"email": "student@example.com", "password": "SecurePassword123"},
        follow_redirects=True,
    )

    resp_owner = client.get(f"/quiz/attempt/{attempt_id}")
    assert resp_owner.status_code == 200
    html = resp_owner.data.decode("utf-8")
    assert "Quiz Results" in html
    assert f"Attempt #{attempt_num}" in html


def test_quiz_result_page_shows_no_pipe_for_short_answers(
    auth_client: FlaskClient, quiz_setup: dict, app: Flask
):
    """Verify result page formats short answers with ' or ' and never renders raw '|'."""
    topic_id = quiz_setup["topic_id"]

    # Add a left-recursion question to this topic
    with app.app_context():
        q_lr = Question(
            topic_id=topic_id,
            type=QuestionType.SHORT,
            question_text="Which recursion causes infinite loop in top-down parsers?",
            correct_answer="left recursion|left-recursive",
            source=QuestionSource.CURRICULUM,
        )
        db.session.add(q_lr)
        db.session.commit()
        q_lr_id = q_lr.id

    # 1. Start quiz to establish active session
    get_resp = auth_client.get(f"/quiz/topic/{topic_id}")
    assert get_resp.status_code == 200

    # 2. Submit form with answers (answering 'left recursive' to the left recursion question)
    with app.app_context():
        questions = Question.query.filter_by(topic_id=topic_id).all()
        post_data = {}
        for q in questions:
            if q.id == q_lr_id:
                post_data[f"question_{q.id}"] = "left recursive"
            elif q.id == quiz_setup["q_short_id"]:
                post_data[f"question_{q.id}"] = "supervised"
            elif q.type == QuestionType.MCQ:
                post_data[f"question_{q.id}"] = "A"
            elif q.type == QuestionType.TF:
                post_data[f"question_{q.id}"] = "True"
            else:
                post_data[f"question_{q.id}"] = "Theory answer text"

    resp = auth_client.post(
        f"/quiz/topic/{topic_id}/submit",
        data=post_data,
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")

    # Verify student answer was evaluated as correct
    assert "✓ Correct" in html

    # Verify short answer questions display alternatives joined with ' or '
    assert "left recursion or left-recursive" in html
    assert "supervised or supervised learning" in html

    # Verify no raw '|' appears anywhere in the rendered HTML
    assert "|" not in html


# ==============================================================================
# 5. Topic Page Sidebar Integration Tests (Requirement 5)
# ==============================================================================

def test_topic_page_shows_take_quiz_button_and_attempt_stats(
    auth_client: FlaskClient, quiz_setup: dict, app: Flask, test_user: User
):
    """Verify topic page shows 'Take Quiz' button and renders last attempt metrics when attempts exist."""
    topic_id = quiz_setup["topic_id"]

    # Initial state: 0 attempts
    r0 = auth_client.get(f"/topics/{topic_id}")
    assert r0.status_code == 200
    html0 = r0.data.decode("utf-8")
    assert "Take Quiz" in html0
    assert "No attempts yet" in html0

    # Add an attempt for test_user
    with app.app_context():
        attempt = Attempt(
            user_id=test_user.id,
            topic_id=topic_id,
            score=3.0,
            total_questions=3,
            wrong_count=0,
            attempt_number=1,
            label=None,
        )
        db.session.add(attempt)
        db.session.commit()

    # Refreshed state: shows attempt count and score
    r1 = auth_client.get(f"/topics/{topic_id}")
    assert r1.status_code == 200
    html1 = r1.data.decode("utf-8")
    assert "Take Quiz" in html1
    assert "Total Attempts:" in html1
    assert "Last Score:" in html1
    assert "3 / 3" in html1
    assert "View last attempt result" in html1


# ==============================================================================
# 6. Question Loader CLI & Validation Tests (Requirement 6)
# ==============================================================================

def test_question_loader_idempotent_ingestion(app: Flask, tmp_path: Path):
    """Verify load-questions command validates and loads without duplicating on re-runs."""
    with app.app_context():
        course = Course(
            code="CS302",
            title="Database Systems",
            semester=4,
            domain="Computer Science",
            credit_hours=3,
            contact_hours="3-0-3",
        )
        db.session.add(course)
        db.session.commit()

        topic = Topic(
            course_id=course.id,
            semester=4,
            subject="Database Systems",
            name="Normalization",
            difficulty=3,
        )
        db.session.add(topic)
        db.session.commit()
        topic_id = topic.id

    csv_content = """semester,subject,topic,type,question_text,option_a,option_b,option_c,option_d,correct_answer,source
4,Database Systems,Normalization,mcq,What does 3NF eliminate?,Partial dependencies,Transitive dependencies,Multi-valued dependencies,Join anomalies,B,curriculum
4,Database Systems,Normalization,tf,2NF requires that all non-key attributes are fully functionally dependent on primary key.,True,False,,,True,curriculum
4,Database Systems,Normalization,short,What normal form requires eliminating multi-valued dependencies?,,,,4NF|fourth normal form,curriculum
4,Database Systems,Normalization,theory,Explain Boyce-Codd Normal Form.,,,,BCNF is a stricter version of 3NF where every determinant must be a candidate key.,curriculum
"""
    test_csv = tmp_path / "test_questions.csv"
    test_csv.write_text(csv_content, encoding="utf-8")

    with app.app_context():
        loader = QuestionLoader(file_path=test_csv)
        s1 = loader.load(dry_run=False)
        assert s1.total_rows == 4
        assert s1.inserted == 4
        assert s1.updated == 0
        assert s1.unchanged == 0
        assert Question.query.filter_by(topic_id=topic_id).count() == 4

        # Second run: strict idempotency, 0 inserted, 4 unchanged
        s2 = loader.load(dry_run=False)
        assert s2.inserted == 0
        assert s2.updated == 0
        assert s2.unchanged == 4
        assert Question.query.filter_by(topic_id=topic_id).count() == 4


def test_question_loader_dry_run_leaves_database_untouched(
    app: Flask, tmp_path: Path
):
    """Verify --dry-run validates and stages but rolls back without persisting changes."""
    with app.app_context():
        course = Course(
            code="CS101",
            title="Intro CS",
            semester=1,
            domain="Core",
            credit_hours=3,
            contact_hours="3-0-3",
        )
        db.session.add(course)
        db.session.commit()

        topic = Topic(
            course_id=course.id,
            semester=1,
            subject="Intro CS",
            name="Variables",
            difficulty=1,
        )
        db.session.add(topic)
        db.session.commit()
        topic_id = topic.id

    csv_content = """semester,subject,topic,type,question_text,option_a,option_b,option_c,option_d,correct_answer,source
1,Intro CS,Variables,tf,Variables store memory values.,True,False,,,True,curriculum
"""
    test_csv = tmp_path / "dry_run.csv"
    test_csv.write_text(csv_content, encoding="utf-8")

    with app.app_context():
        loader = QuestionLoader(file_path=test_csv)
        summary = loader.load(dry_run=True)
        assert summary.dry_run is True
        assert summary.inserted == 1
        # In database, question count must still be 0
        assert Question.query.filter_by(topic_id=topic_id).count() == 0


def test_question_loader_fails_fast_on_validation_errors(
    app: Flask, tmp_path: Path
):
    """Verify loader accumulates validation errors and rejects invalid input before saving."""
    invalid_csv = """semester,subject,topic,type,question_text,option_a,option_b,option_c,option_d,correct_answer,source
99,FakeSubject,FakeTopic,invalid_type,,,,,A,unknown_source
"""
    test_csv = tmp_path / "invalid.csv"
    test_csv.write_text(invalid_csv, encoding="utf-8")

    with app.app_context():
        loader = QuestionLoader(file_path=test_csv)
        with pytest.raises(QuestionsValidationError) as exc_info:
            loader.load()

        err_msg = str(exc_info.value)
        assert "between 1 and 8" in err_msg
        assert "Topic not found" in err_msg
        assert "Invalid question type" in err_msg
        assert "'question_text' cannot be empty" in err_msg


def test_question_loader_cli_command(app: Flask):
    """Verify that flask load-questions CLI command runs successfully."""
    runner = app.test_cli_runner()
    # Execute against data/questions.csv with --dry-run
    # Note: data/questions.csv topics must exist in db first, so load curriculum
    from app.services.curriculum_loader import load_curriculum
    with app.app_context():
        load_curriculum(data_dir="data", dry_run=False)

    result = runner.invoke(args=["load-questions", "--dry-run"])
    assert result.exit_code == 0
    assert "StudySphere Questions Ingestion Summary" in result.output
    assert "Records Read    : 24" in result.output
    assert "DRY RUN" in result.output
