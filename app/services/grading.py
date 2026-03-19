"""
QuizzMaster Backend - Grading Service
Auto-grading logic for quiz submissions.
"""
from datetime import datetime, timezone
from typing import Dict

from sqlalchemy.orm import Session

from app.models import Submission, Quiz, Question, Answer


def _grade_choice(answer_value: str, options: list) -> bool:
    """Grade a multiple_choice or true_false answer.
    Returns True if the selected option id matches an option where is_correct=True.
    """
    if not answer_value or not options:
        return False

    for option in options:
        if option.get("id") == answer_value and option.get("is_correct", False):
            return True
    return False


def _grade_short_answer(answer_value: str, options: list) -> bool:
    """Grade a short_answer question.
    Case-insensitive, whitespace-stripped match against all accepted answers.
    """
    if not answer_value or not options:
        return False

    normalized_answer = answer_value.strip().lower()
    for option in options:
        accepted = option.get("text", "").strip().lower()
        if normalized_answer == accepted:
            return True
    return False


def grade_submission(submission: Submission, quiz: Quiz, db: Session) -> Submission:
    """Grade all answers in a submission and update scores.
    
    Grading rules:
    - Multiple choice / true_false: check selected option id against is_correct
    - Short answer: case-insensitive, whitespace-stripped match
    - No partial credit — full points or zero
    - Unanswered questions (null answer_value) always score zero
    """
    # Build question lookup map
    question_map: Dict[int, Question] = {q.id: q for q in quiz.questions}

    total_score = 0.0
    max_score = 0.0

    for answer in submission.answers:
        question = question_map.get(answer.question_id)

        if not question:
            # Unknown question ID — mark as incorrect
            answer.is_correct = False
            answer.points_awarded = 0.0
            continue

        max_score += question.points

        if answer.answer_value is None:
            # Unanswered — zero points
            answer.is_correct = False
            answer.points_awarded = 0.0
            continue

        # Grade based on question type
        is_correct = False
        if question.question_type in ("multiple_choice", "true_false"):
            is_correct = _grade_choice(answer.answer_value, question.options or [])
        elif question.question_type == "short_answer":
            is_correct = _grade_short_answer(answer.answer_value, question.options or [])

        answer.is_correct = is_correct
        answer.points_awarded = question.points if is_correct else 0.0

        if is_correct:
            total_score += question.points

    # Also account for questions that weren't answered at all
    answered_question_ids = {a.question_id for a in submission.answers}
    for q_id, question in question_map.items():
        if q_id not in answered_question_ids:
            max_score += question.points

    # Update submission totals
    submission.score = total_score
    submission.max_score = max_score
    submission.percentage = (total_score / max_score * 100) if max_score > 0 else 0.0
    submission.graded_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(submission)
    return submission
