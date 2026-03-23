"""
QuizzMaster Backend - Submissions Router
Submit quiz answers, list submissions, get submission details.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import User, Quiz, Submission, Answer
from app.schemas import (
    SubmissionCreate, SubmissionOut, SubmissionDetailOut, AnswerDetailOut, 
    GenericResponse, PaginatedResponse
)
from app.core.dependencies import get_current_user, get_current_instructor
from app.utils.pagination import paginate
from app.utils.search import apply_search
from app.services.grading import grade_submission

router = APIRouter()

@router.post("/quiz/{quiz_id}", response_model=GenericResponse[SubmissionOut], status_code=status.HTTP_201_CREATED)
def submit_quiz(
    quiz_id: str,
    submission_data: SubmissionCreate,
    request: Request,
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

    # Check attempt limit
    attempts = (
        db.query(Submission)
        .filter(Submission.quiz_id == quiz_id, Submission.student_id == current_user.id)
        .count()
    )
    if quiz.max_attempts and attempts >= quiz.max_attempts:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Maximum attempts ({quiz.max_attempts}) reached for this quiz.",
        )

    # Metadata extraction
    user_agent_str = request.headers.get("user-agent", "")
    ip_address = request.client.host if request.client else None
    
    # Simple UA parsing
    browser = "Unknown"
    os = "Unknown"
    if "Chrome" in user_agent_str: browser = "Chrome"
    elif "Firefox" in user_agent_str: browser = "Firefox"
    elif "Safari" in user_agent_str: browser = "Safari"
    elif "Edge" in user_agent_str: browser = "Edge"
    
    if "Windows" in user_agent_str: os = "Windows"
    elif "Mac" in user_agent_str: os = "macOS"
    elif "Linux" in user_agent_str: os = "Linux"
    elif "Android" in user_agent_str: os = "Android"
    elif "iPhone" in user_agent_str or "iPad" in user_agent_str: os = "iOS"

    # Location Mock (In production, use a GEOLite2 DB or IpInfo API)
    location = "0.0, 0.0" # Default
    if ip_address and ip_address != "127.0.0.1":
        # Placeholder for lat/long
        location = "37.7749, -122.4194" # Mock San Francisco

    # Create submission
    submission = Submission(
        quiz_id=quiz_id,
        student_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent_str,
        browser=browser,
        os=os,
        location=location,
    )
    db.add(submission)
    db.flush()

    # Answer map for easy lookup
    provided_answers = {a.question_id: a.answer_value for a in submission_data.answers}
    
    # Create answer records for ALL questions (handle unattended)
    for q in quiz.questions:
        val = provided_answers.get(q.id)
        # Note: val can be None, which means unattended
        answer = Answer(
            submission_id=submission.id,
            question_id=q.id,
            answer_value=val,
        )
        db.add(answer)

    db.flush()
    db.refresh(submission)

    # Auto-grade
    submission = grade_submission(submission, quiz, db)

    return GenericResponse(data=submission)


@router.get("/my", response_model=GenericResponse[PaginatedResponse[SubmissionDetailOut]])
def list_my_submissions(
    search: str = None,
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all submissions by the current user with pagination and search on quiz title."""
    query = (
        db.query(Submission)
        .join(Quiz, Submission.quiz_id == Quiz.id)
        .filter(Submission.student_id == current_user.id)
    )
    
    if search:
        query = query.filter(Quiz.title.ilike(f"%{search}%"))
        
    query = query.order_by(Submission.submitted_at.desc())
    
    pagination_result = paginate(query, page, limit)
    submissions = pagination_result["items"]
    
    items = []
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
            quiz_title=sub.quiz.title if sub.quiz else "Deleted Quiz",
            answers=[],
            ip_address=sub.ip_address,
            user_agent=sub.user_agent,
            browser=sub.browser,
            os=sub.os,
            location=sub.location,
        )
        items.append(detail)
        
    return GenericResponse(data={
        "items": items,
        "pagination": pagination_result["pagination"]
    })


@router.get("/my/{submission_id}", response_model=SubmissionDetailOut)
def get_my_submission(
    submission_id: str,
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
        ip_address=submission.ip_address,
        user_agent=submission.user_agent,
        browser=submission.browser,
        os=submission.os,
        location=submission.location,
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


@router.get("/quiz/{quiz_id}", response_model=GenericResponse[PaginatedResponse[SubmissionDetailOut]])
def list_quiz_submissions(
    quiz_id: str,
    search: str = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
):
    """List all submissions for a specific quiz (instructor only) with search and pagination."""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.instructor_id == current_user.id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    query = (
        db.query(Submission)
        .join(User, Submission.student_id == User.id)
        .filter(Submission.quiz_id == quiz_id)
    )
    
    # Generic Search on student username
    if search:
        query = query.filter(User.username.ilike(f"%{search}%"))
        
    query = query.order_by(Submission.submitted_at.desc())
    
    # Standard Pagination
    pagination_result = paginate(query, page, limit)
    submissions = pagination_result["items"]

    items = []
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
            ip_address=sub.ip_address,
            user_agent=sub.user_agent,
            browser=sub.browser,
            os=sub.os,
            location=sub.location,
        )
        items.append(detail)

    return GenericResponse(data={
        "items": items,
        "pagination": pagination_result["pagination"]
    })
