"""Quiz blueprint for taking tests, recording attempts, and theory self-evaluation."""

from __future__ import annotations
import math
from typing import Any
from flask import (
    Blueprint,
    render_template,
    abort,
    redirect,
    url_for,
    request,
    session,
    flash,
    jsonify,
)
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from app.extensions import db
from app.models.topic import Topic
from app.models.question import Question, QuestionType
from app.models.attempt import Attempt
from app.models.attempt_answer import AttemptAnswer, SelfRating
from app.services.label_service import label_attempt_record
from app.services.quiz_engine import (
    get_topic_quiz_questions,
    score_quiz,
    evaluate_single_answer,
    QuestionResultDetail,
    calculate_attempts_history,
)

quiz_bp: Blueprint = Blueprint("quiz", __name__)

MAX_ANSWER_LENGTH: int = 5000
VALID_RATINGS: set[str] = {
    SelfRating.GOT_IT.value,
    SelfRating.PARTLY.value,
    SelfRating.MISSED.value,
}


def _parse_self_grade_input(req: Any) -> dict[int, str]:
    """Extract question_id -> rating mapping from request body (form or JSON).

    Supports multiple payload formats:
    - Form: question_id=1, rating=got_it
    - Form: question_1=got_it
    - JSON: {"question_id": 1, "rating": "got_it"}
    - JSON: {"ratings": {1: "got_it", ...}}
    - JSON: {"1": "got_it"}

    Args:
        req: Flask Request object.

    Returns:
        dict[int, str]: Mapping from question ID to rating string.
    """
    ratings: dict[int, str] = {}

    if req.is_json:
        data = req.get_json(silent=True) or {}
        if isinstance(data, dict):
            if "question_id" in data and "rating" in data:
                try:
                    qid = int(data["question_id"])
                    ratings[qid] = str(data["rating"]).strip().lower()
                except (ValueError, TypeError):
                    pass

            nested = data.get("ratings")
            if isinstance(nested, dict):
                for k, v in nested.items():
                    try:
                        qid = int(k)
                        ratings[qid] = str(v).strip().lower()
                    except (ValueError, TypeError):
                        pass

            for k, v in data.items():
                if k in ("question_id", "rating", "ratings", "csrf_token"):
                    continue
                k_clean = str(k).replace("question_", "").replace("q_", "")
                if k_clean.isdigit():
                    ratings[int(k_clean)] = str(v).strip().lower()
    else:
        qid_val = req.form.get("question_id")
        rating_val = req.form.get("rating")
        if qid_val is not None and rating_val is not None:
            try:
                ratings[int(qid_val)] = str(rating_val).strip().lower()
            except (ValueError, TypeError):
                pass

        for k, v in req.form.items():
            if k in ("question_id", "rating", "csrf_token"):
                continue
            k_clean = (
                str(k)
                .replace("question_", "")
                .replace("rating_", "")
                .replace("q_", "")
            )
            if k_clean.isdigit():
                ratings[int(k_clean)] = str(v).strip().lower()

    return ratings


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

    # Security: Store served question IDs and topic ID in signed session
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
    """Evaluate student answers, persist attempt and attempt answers, and redirect."""
    topic = db.session.get(Topic, topic_id)
    if topic is None:
        abort(404)

    served_ids = session.get("quiz_question_ids")
    session_topic_id = session.get("quiz_topic_id")

    if not served_ids or session_topic_id != topic.id:
        flash("Your quiz session has expired or is invalid. Please start again.", "warning")
        return redirect(url_for("quiz.topic_quiz", topic_id=topic.id))

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
        clean_val = str(raw_val)[:MAX_ANSWER_LENGTH]
        student_answers[q.id] = clean_val

    # Score answers via evaluation engine (theory questions excluded from score/total_questions)
    score_result = score_quiz(ordered_questions, student_answers)

    # Calculate attempt number = previous attempts of this user and topic + 1
    previous_attempts_count = Attempt.query.filter_by(
        user_id=current_user.id,
        topic_id=topic.id,
    ).count()
    attempt_number = previous_attempts_count + 1

    # Persist Attempt and all AttemptAnswer records in the same transaction
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
    db.session.flush()

    # Predict initial mastery label from auto-scored questions inside the same transaction
    label_attempt_record(attempt, commit=False)

    for q in ordered_questions:
        ans_text = student_answers.get(q.id, "")
        is_corr = evaluate_single_answer(q, ans_text)
        attempt_answer = AttemptAnswer(
            attempt_id=attempt.id,
            question_id=q.id,
            answer_text=ans_text,
            is_correct=is_corr,
            self_rating=None,
        )
        db.session.add(attempt_answer)

    db.session.commit()

    # Remove answers and active quiz state from session; result page reads from DB
    session.pop("quiz_question_ids", None)
    session.pop("quiz_topic_id", None)
    session.pop(f"quiz_attempt_{attempt.id}", None)
    session.modified = True

    return redirect(url_for("quiz.attempt_result", attempt_id=attempt.id))


@quiz_bp.route("/attempt/<int:attempt_id>", methods=["GET"])
@login_required
def attempt_result(attempt_id: int):
    """Render quiz assessment results page directly from the database."""
    attempt = (
        Attempt.query.options(
            joinedload(Attempt.topic).joinedload(Topic.course),
            joinedload(Attempt.answers).joinedload(AttemptAnswer.question),
        )
        .filter_by(id=attempt_id)
        .first()
    )
    # Owner-only restriction: 404 for nonexistent or other users' attempts
    if attempt is None or attempt.user_id != current_user.id:
        abort(404)

    percentage = (
        round((attempt.score / attempt.total_questions * 100.0), 1)
        if attempt.total_questions > 0
        else 0.0
    )

    details: list[QuestionResultDetail] = []
    has_ungraded_theory: bool = False

    if attempt.answers:
        # Reconstruct review from durable database AttemptAnswer rows
        for ans in attempt.answers:
            q = ans.question
            q_type_str = (
                q.type.value if hasattr(q.type, "value") else str(q.type)
            ).lower()

            if q_type_str == QuestionType.THEORY.value and ans.self_rating is None:
                has_ungraded_theory = True

            details.append(
                QuestionResultDetail(
                    question_id=ans.question_id,
                    question_text=q.question_text,
                    question_type=q_type_str,
                    student_answer=ans.answer_text,
                    correct_answer=q.correct_answer,
                    is_correct=ans.is_correct,
                    options=q.options,
                    self_rating=ans.self_rating,
                )
            )
    else:
        # Backward-compatibility fallback for direct test objects without answers
        questions = (
            Question.query.filter_by(topic_id=attempt.topic_id)
            .limit(attempt.total_questions or 10)
            .all()
        )
        score_result = score_quiz(questions, {})
        details = score_result.details

    return render_template(
        "quiz/result.html",
        attempt=attempt,
        topic=attempt.topic,
        percentage=percentage,
        details=details,
        has_ungraded_theory=has_ungraded_theory,
    )


@quiz_bp.route("/attempt/<int:attempt_id>/self-grade", methods=["POST"])
@login_required
def self_grade(attempt_id: int):
    """Accept theory question self-evaluations, update score/wrong counts, and persist."""
    attempt = db.session.get(Attempt, attempt_id)
    if attempt is None or attempt.user_id != current_user.id:
        abort(404)

    submitted_ratings = _parse_self_grade_input(request)

    # Fetch attempt answers for this attempt
    answers = (
        AttemptAnswer.query.options(joinedload(AttemptAnswer.question))
        .filter_by(attempt_id=attempt.id)
        .all()
    )
    answer_map = {ans.question_id: ans for ans in answers}

    for qid, rating in submitted_ratings.items():
        if rating not in VALID_RATINGS:
            continue
        if qid not in answer_map:
            # Ignore unknown question ids
            continue

        ans = answer_map[qid]
        q_type_str = (
            ans.question.type.value
            if hasattr(ans.question.type, "value")
            else str(ans.question.type)
        ).lower()

        if q_type_str != QuestionType.THEORY.value:
            # Ignore non-theory questions
            continue

        # Update rating in place (no duplicate rows)
        ans.self_rating = rating

    # Recalculate attempt score, wrong_count, and total_questions consistently
    auto_score = 0.0
    auto_wrong = 0.0
    auto_count = 0
    theory_score = 0.0
    theory_wrong = 0.0
    theory_count = 0

    for ans in answers:
        q_type = (
            ans.question.type.value
            if hasattr(ans.question.type, "value")
            else str(ans.question.type)
        ).lower()

        if q_type == QuestionType.THEORY.value:
            if ans.self_rating == SelfRating.GOT_IT.value:
                theory_score += 1.0
                theory_count += 1
            elif ans.self_rating == SelfRating.PARTLY.value:
                theory_score += 0.5
                theory_wrong += 0.5
                theory_count += 1
            elif ans.self_rating == SelfRating.MISSED.value:
                theory_wrong += 1.0
                theory_count += 1
            # Unrated theory questions remain excluded from total and score
        else:
            auto_count += 1
            if ans.is_correct:
                auto_score += 1.0
            else:
                auto_wrong += 1.0

    attempt.score = auto_score + theory_score
    attempt.wrong_count = auto_wrong + theory_wrong
    attempt.total_questions = auto_count + theory_count

    # Recompute Decision Tree mastery label after theory self-evaluation updates scores
    label_attempt_record(attempt, commit=False)

    db.session.commit()

    percentage = (
        round((attempt.score / attempt.total_questions * 100.0), 1)
        if attempt.total_questions > 0
        else 0.0
    )

    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify(
            {
                "status": "success",
                "score": attempt.score,
                "total_questions": attempt.total_questions,
                "wrong_count": attempt.wrong_count,
                "percentage": percentage,
                "label": attempt.label.value if attempt.label else None,
            }
        )

    flash("Theory self-evaluation recorded successfully.", "success")
    return redirect(url_for("quiz.attempt_result", attempt_id=attempt.id))


@quiz_bp.route("/topic/<int:topic_id>/history", methods=["GET"])
@login_required
def topic_quiz_history(topic_id: int):
    """Render complete chronological quiz attempt history for the current user on a topic."""
    topic = (
        Topic.query.options(joinedload(Topic.course))
        .filter_by(id=topic_id)
        .first()
    )
    if topic is None:
        abort(404)

    # ONE query with joinedload for topic and course (no N+1)
    user_attempts = (
        Attempt.query.options(
            joinedload(Attempt.topic).joinedload(Topic.course)
        )
        .filter(Attempt.user_id == current_user.id, Attempt.topic_id == topic.id)
        .order_by(Attempt.attempt_number.asc(), Attempt.id.asc())
        .all()
    )

    history_items = calculate_attempts_history(user_attempts)

    return render_template(
        "quiz/topic_history.html",
        topic=topic,
        history_items=history_items,
        total_attempts=len(user_attempts),
    )


@quiz_bp.route("/history", methods=["GET"])
@login_required
def history():
    """Render paginated global quiz attempt history across all topics for the current user."""
    raw_page = request.args.get("page", "1")
    try:
        page = int(raw_page)
        if page < 1:
            page = 1
    except (ValueError, TypeError):
        page = 1

    per_page = 20

    # ONE query with joinedload for topic and course (no N+1)
    attempts = (
        Attempt.query.options(
            joinedload(Attempt.topic).joinedload(Topic.course)
        )
        .filter(Attempt.user_id == current_user.id)
        .order_by(Attempt.created_at.desc(), Attempt.id.desc())
        .all()
    )

    total_attempts = len(attempts)
    distinct_topic_ids = {a.topic_id for a in attempts}
    topics_attempted_count = len(distinct_topic_ids)

    percentages = [
        round((a.score / a.total_questions * 100.0), 1)
        for a in attempts
        if a.total_questions > 0
    ]
    avg_percentage = (
        round(sum(percentages) / len(percentages), 1) if percentages else 0.0
    )

    total_pages = max(1, math.ceil(total_attempts / per_page)) if total_attempts > 0 else 1
    if page > total_pages:
        page = total_pages

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_attempts = attempts[start_idx:end_idx]

    items = [
        {
            "attempt": a,
            "percentage": (
                round((a.score / a.total_questions * 100.0), 1)
                if a.total_questions > 0
                else 0.0
            ),
        }
        for a in page_attempts
    ]

    return render_template(
        "quiz/history.html",
        items=items,
        total_attempts=total_attempts,
        topics_attempted_count=topics_attempted_count,
        avg_percentage=avg_percentage,
        page=page,
        total_pages=total_pages,
        has_prev=page > 1,
        has_next=page < total_pages,
    )
