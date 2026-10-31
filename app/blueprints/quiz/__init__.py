"""Quiz blueprint for taking tests, recording attempts, and triggering ML evaluation."""

from __future__ import annotations
from flask import (
    Blueprint,
    render_template,
    abort,
    redirect,
    url_for,
    request,
    session,
    flash,
)
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from app.extensions import db
from app.models.topic import Topic
from app.models.question import Question
from app.models.attempt import Attempt
from app.services.quiz_engine import (
    get_topic_quiz_questions,
    score_quiz,
)

quiz_bp: Blueprint = Blueprint("quiz", __name__)

MAX_ANSWER_LENGTH: int = 5000


@quiz_bp.route("/topic/<int:topic_id>", methods=["GET"])
@login_required
def topic_quiz(topic_id: int):
    """Present assessment quiz form with up to 10 randomized questions for the topic."""
    topic = (
        Topic.query.options(joinedload(Topic.course))
        .filter_by(id=topic_id)
        .first()
    )
    if topic is None:
        abort(404)

    questions = get_topic_quiz_questions(topic.id, limit=10, shuffle=True)
    if not questions:
        return render_template("quiz/no_questions.html", topic=topic), 200

    # Security: Store the served question IDs and topic ID in the signed session
    # so submitted answers cannot tamper with question set or reference unauthorized IDs
    session["quiz_topic_id"] = topic.id
    session["quiz_question_ids"] = [q.id for q in questions]
    session.modified = True

    return render_template(
        "quiz/take.html",
        topic=topic,
        questions=questions,
    )


@quiz_bp.route("/topic/<int:topic_id>/submit", methods=["POST"])
@login_required
def submit_quiz(topic_id: int):
    """Evaluate student answers, persist attempt metrics, and redirect to result page."""
    topic = db.session.get(Topic, topic_id)
    if topic is None:
        abort(404)

    served_ids = session.get("quiz_question_ids")
    session_topic_id = session.get("quiz_topic_id")

    if not served_ids or session_topic_id != topic.id:
        flash("Your quiz session has expired or is invalid. Please start again.", "warning")
        return redirect(url_for("quiz.topic_quiz", topic_id=topic.id))

    served_id_set = set(served_ids)

    # Fetch Question entities corresponding to served IDs for this topic
    questions = (
        Question.query.filter(
            Question.id.in_(served_ids),
            Question.topic_id == topic.id,
        )
        .all()
    )
    q_map = {q.id: q for q in questions}
    ordered_questions = [q_map[qid] for qid in served_ids if qid in q_map]

    # Collect student answers from form, ignoring unknown question IDs and limiting length
    student_answers: dict[int, str] = {}
    for q in ordered_questions:
        raw_val = request.form.get(f"question_{q.id}", "")
        # Enforce maximum answer character length
        clean_val = str(raw_val)[:MAX_ANSWER_LENGTH].strip()
        student_answers[q.id] = clean_val

    # Score answers via evaluation engine
    score_result = score_quiz(ordered_questions, student_answers)

    # Calculate attempt number = previous attempts of this user and topic + 1
    previous_attempts_count = Attempt.query.filter_by(
        user_id=current_user.id,
        topic_id=topic.id,
    ).count()
    attempt_number = previous_attempts_count + 1

    attempt = Attempt(
        user_id=current_user.id,
        topic_id=topic.id,
        score=score_result.score,
        total_questions=score_result.total_questions,
        wrong_count=score_result.wrong_count,
        attempt_number=attempt_number,
        label=None,
    )
    db.session.add(attempt)
    db.session.commit()

    # Store detailed question responses in signed session for owner review
    session[f"quiz_attempt_{attempt.id}"] = {
        "served_ids": [q.id for q in ordered_questions],
        "user_answers": {str(qid): ans for qid, ans in student_answers.items()},
    }
    # Clear in-flight active quiz state from session
    session.pop("quiz_question_ids", None)
    session.pop("quiz_topic_id", None)
    session.modified = True

    return redirect(url_for("quiz.attempt_result", attempt_id=attempt.id))


@quiz_bp.route("/attempt/<int:attempt_id>", methods=["GET"])
@login_required
def attempt_result(attempt_id: int):
    """Render quiz assessment results page, strictly accessible only to the attempt owner."""
    attempt = (
        Attempt.query.options(joinedload(Attempt.topic).joinedload(Topic.course))
        .filter_by(id=attempt_id)
        .first()
    )
    # Owner-only restriction: 404 for other users
    if attempt is None or attempt.user_id != current_user.id:
        abort(404)

    percentage = (
        round((attempt.score / attempt.total_questions * 100.0), 1)
        if attempt.total_questions > 0
        else 0.0
    )

    # Reconstruct question-level review from session data or topic fallback
    attempt_data = session.get(f"quiz_attempt_{attempt.id}")
    student_answers: dict[int, str] = {}
    questions: list[Question] = []

    if attempt_data and "served_ids" in attempt_data:
        served_ids = attempt_data["served_ids"]
        raw_answers = attempt_data.get("user_answers", {})
        student_answers = {int(k): v for k, v in raw_answers.items() if str(k).isdigit()}

        db_questions = Question.query.filter(Question.id.in_(served_ids)).all()
        q_map = {q.id: q for q in db_questions}
        questions = [q_map[qid] for qid in served_ids if qid in q_map]
    else:
        # Fallback when session has expired or attempt is viewed in a different session
        questions = (
            Question.query.filter_by(topic_id=attempt.topic_id)
            .limit(attempt.total_questions or 10)
            .all()
        )

    score_result = score_quiz(questions, student_answers)

    return render_template(
        "quiz/result.html",
        attempt=attempt,
        topic=attempt.topic,
        percentage=percentage,
        details=score_result.details,
    )
