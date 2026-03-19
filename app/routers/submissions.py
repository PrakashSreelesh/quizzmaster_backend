"""
QuizzMaster Backend - Submissions Router
Submit quiz answers, list submissions, get submission details.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import User, Quiz, Submission, Answer
from app.schemas import SubmissionCreate, SubmissionOut, SubmissionDetailOut, AnswerDetailOut
from app.core.dependencies import get_current_user, get_current_instructor
from app.services.grading import grade_submission

router = APIRouter()


@router.post("/quiz/{quiz_id}", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
def submit_quiz(
    quiz_id: int,
    submission_data: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit answers for a quiz. Auto-graded immediately."""
    # Verify quiz exists and is published
    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id, Quiz.is_published == True)
        .options(joinedload(Quiz.questions))
        .first()
    )
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Published quiz not found",
        )

    # Check for duplicate submission
    existing = (
        db.query(Submission)
        .filter(Submission.quiz_id == quiz_id, Submission.student_id == current_user.id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted this quiz",
        )

    # Create submission (ungraded)
    submission = Submission(
        quiz_id=quiz_id,
        student_id=current_user.id,
    )
    db.add(submission)
    db.flush()  # Get submission.id

    # Create answer records
    for answer_data in submission_data.answers:
        answer = Answer(
            submission_id=submission.id,
            question_id=answer_data.question_id,
            answer_value=answer_data.answer_value,
        )
        db.add(answer)

    db.flush()
    db.refresh(submission)

    # Auto-grade
    submission = grade_submission(submission, quiz, db)

    return submission


@router.get("/my", response_model=List[SubmissionOut])
def list_my_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all submissions by the current user."""
    submissions = (
        db.query(Submission)
        .filter(Submission.student_id == current_user.id)
        .options(joinedload(Submission.answers))
        .order_by(Submission.submitted_at.desc())
        .all()
    )
    return submissions


@router.get("/my/{submission_id}", response_model=SubmissionDetailOut)
def get_my_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific submission with detailed answer feedback."""
    submission = (
        db.query(Submission)
        .filter(Submission.id == submission_id, Submission.student_id == current_user.id)
        .options(
            joinedload(Submission.answers).joinedload(Answer.question),
            joinedload(Submission.quiz),
        )
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Build detailed response with question text and correct answers
    detail = SubmissionDetailOut(
        id=submission.id,
        quiz_id=submission.quiz_id,
        student_id=submission.student_id,
        score=submission.score,
        max_score=submission.max_score,
        percentage=submission.percentage,
        submitted_at=submission.submitted_at,
        graded_at=submission.graded_at,
        quiz_title=submission.quiz.title if submission.quiz else None,
        answers=[],
    )
    for ans in submission.answers:
        correct_answer = None
        question_text = None
        if ans.question:
            question_text = ans.question.text
            # Extract correct answer for feedback
            if ans.question.question_type in ("multiple_choice", "true_false"):
                for opt in (ans.question.options or []):
                    if opt.get("is_correct"):
                        correct_answer = opt.get("id", opt.get("text", ""))
                        break
            elif ans.question.question_type == "short_answer":
                correct_answers = [opt.get("text", "") for opt in (ans.question.options or [])]
                correct_answer = correct_answers[0] if correct_answers else None

        detail.answers.append(AnswerDetailOut(
            id=ans.id,
            question_id=ans.question_id,
            answer_value=ans.answer_value,
            is_correct=ans.is_correct,
            points_awarded=ans.points_awarded,
            question_text=question_text,
            correct_answer=correct_answer,
        ))

    return detail


@router.get("/quiz/{quiz_id}", response_model=List[SubmissionDetailOut])
def list_quiz_submissions(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
):
    """List all submissions for a specific quiz (instructor only)."""
    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id, Quiz.instructor_id == current_user.id)
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    submissions = (
        db.query(Submission)
        .filter(Submission.quiz_id == quiz_id)
        .options(
            joinedload(Submission.answers).joinedload(Answer.question),
            joinedload(Submission.student),
        )
        .order_by(Submission.submitted_at.desc())
        .all()
    )

    results = []
    for sub in submissions:
        detail = SubmissionDetailOut(
            id=sub.id,
            quiz_id=sub.quiz_id,
            student_id=sub.student_id,
            score=sub.score,
            max_score=sub.max_score,
            percentage=sub.percentage,
            submitted_at=sub.submitted_at,
            graded_at=sub.graded_at,
            quiz_title=quiz.title,
            student_name=sub.student.username if sub.student else None,
            answers=[],
        )
        for ans in sub.answers:
            question_text = ans.question.text if ans.question else None
            correct_answer = None
            if ans.question:
                if ans.question.question_type in ("multiple_choice", "true_false"):
                    for opt in (ans.question.options or []):
                        if opt.get("is_correct"):
                            correct_answer = opt.get("id", opt.get("text", ""))
                            break
                elif ans.question.question_type == "short_answer":
                    correct_answers = [opt.get("text", "") for opt in (ans.question.options or [])]
                    correct_answer = correct_answers[0] if correct_answers else None

            detail.answers.append(AnswerDetailOut(
                id=ans.id,
                question_id=ans.question_id,
                answer_value=ans.answer_value,
                is_correct=ans.is_correct,
                points_awarded=ans.points_awarded,
                question_text=question_text,
                correct_answer=correct_answer,
            ))
        results.append(detail)

    return results
