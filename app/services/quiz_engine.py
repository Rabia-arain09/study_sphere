"""Quiz engine service for question scoring, random selection, and evaluation."""

from __future__ import annotations
import random
from dataclasses import dataclass
from typing import Any
from app.models.question import Question, QuestionType


@dataclass
class QuestionResultDetail:
    """Detailed evaluation result for a single question response in an attempt."""

    question_id: int
    question_text: str
    question_type: str
    student_answer: str
    correct_answer: str
    is_correct: bool | None  # None for non-auto-scored theory questions
    options: dict[str, Any] | list[Any] | None = None


@dataclass
class QuizScoreResult:
    """Aggregated assessment result scoring auto-evaluated question responses."""

    score: float
    total_questions: int
    wrong_count: int
    percentage: float
    details: list[QuestionResultDetail]


def evaluate_single_answer(
    question: Question,
    student_answer: str | None,
) -> bool | None:
    """Evaluate a student's answer against the question's ground-truth correct answer.

    Evaluation rules:
    - MCQ: compared case-insensitively against correct option key or option text.
    - TF: compared case-insensitively ('true'/'false').
    - SHORT: compared case-insensitively after trimming. Supports multiple '|'-separated accepted answers.
    - THEORY: NOT auto-scored. Returns None (excluded from score and total_questions).

    Args:
        question: Question entity.
        student_answer: Raw string submitted by the student, or None.

    Returns:
        bool | None: True if correct, False if wrong, None if theory/non-scorable.
    """
    q_type_str = (
        question.type.value if hasattr(question.type, "value") else str(question.type)
    ).lower()

    # Theory questions are not auto-scored
    if q_type_str == QuestionType.THEORY.value:
        return None

    clean_student = (student_answer or "").strip()
    clean_correct = (question.correct_answer or "").strip()

    if q_type_str == QuestionType.MCQ.value:
        # Match option key (e.g., 'A', 'B') case-insensitively
        if clean_student.upper() == clean_correct.upper():
            return True

        # Also support matching the option label text if options dict is present
        if isinstance(question.options, dict):
            # If student submitted option text that matches the correct option key's text
            correct_val = str(question.options.get(clean_correct.upper(), "")).strip()
            if correct_val and clean_student.lower() == correct_val.lower():
                return True
            # If correct_answer was text and student submitted the matching key
            for key, val in question.options.items():
                if str(val).strip().lower() == clean_correct.lower():
                    if clean_student.upper() == str(key).strip().upper():
                        return True
                    if clean_student.lower() == str(val).strip().lower():
                        return True

        return False

    if q_type_str == QuestionType.TF.value:
        return clean_student.lower() == clean_correct.lower()

    if q_type_str == QuestionType.SHORT.value:
        if not clean_student:
            return False
        # Multiple accepted answers separated by '|'
        accepted_variants = [
            variant.strip().lower()
            for variant in clean_correct.split("|")
            if variant.strip()
        ]
        return clean_student.lower() in accepted_variants

    return False


def score_quiz(
    questions: list[Question],
    student_answers: dict[int, str],
) -> QuizScoreResult:
    """Score a collection of question responses and generate an aggregated evaluation result.

    Excludes theory questions from `score`, `total_questions`, and `wrong_count`.

    Args:
        questions: Ordered list of Question models served to the student.
        student_answers: Mapping from question ID to student submitted answer string.

    Returns:
        QuizScoreResult: Score breakdown and per-question details.
    """
    details: list[QuestionResultDetail] = []
    correct_count = 0
    scorable_count = 0
    wrong_count = 0

    for q in questions:
        raw_ans = student_answers.get(q.id, "")
        is_correct = evaluate_single_answer(q, raw_ans)

        q_type_str = (
            q.type.value if hasattr(q.type, "value") else str(q.type)
        ).lower()

        if is_correct is not None:
            scorable_count += 1
            if is_correct:
                correct_count += 1
            else:
                wrong_count += 1

        details.append(
            QuestionResultDetail(
                question_id=q.id,
                question_text=q.question_text,
                question_type=q_type_str,
                student_answer=raw_ans,
                correct_answer=q.correct_answer,
                is_correct=is_correct,
                options=q.options,
            )
        )

    score_val = float(correct_count)
    percentage = (
        round((score_val / scorable_count * 100.0), 1) if scorable_count > 0 else 0.0
    )

    return QuizScoreResult(
        score=score_val,
        total_questions=scorable_count,
        wrong_count=wrong_count,
        percentage=percentage,
        details=details,
    )


def get_topic_quiz_questions(
    topic_id: int,
    limit: int = 10,
    shuffle: bool = True,
) -> list[Question]:
    """Select up to `limit` random questions for a topic.

    Args:
        topic_id: Target topic primary key.
        limit: Maximum number of questions to pick (default 10).
        shuffle: Whether to randomize the order.

    Returns:
        list[Question]: Selected Question instances.
    """
    questions = Question.query.filter_by(topic_id=topic_id).all()
    if not questions:
        return []

    if len(questions) <= limit:
        selected = list(questions)
        if shuffle:
            random.shuffle(selected)
        return selected

    return random.sample(questions, limit)
