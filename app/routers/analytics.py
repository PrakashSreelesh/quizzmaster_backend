"""
QuizzMaster Backend - Analytics Router
Quiz analytics, student analytics, leaderboard, and platform summary.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Quiz
from app.schemas import QuizAnalytics, StudentAnalytics, PlatformSummary, LeaderboardEntry
from app.core.dependencies import get_current_user, get_current_instructor
from app.services.analytics import (
    get_quiz_analytics,
    get_student_analytics,
    get_quiz_leaderboard,
    get_platform_summary,
)

router = APIRouter()


@router.get("/quiz/{quiz_id}", response_model=QuizAnalytics)
def quiz_analytics(
    quiz_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
):
    """Get analytics for a specific quiz (instructor only, must own the quiz)."""
    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id, Quiz.instructor_id == current_user.id)
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    return get_quiz_analytics(quiz, db)


@router.get("/quiz/{quiz_id}/leaderboard", response_model=List[LeaderboardEntry])
def quiz_leaderboard(
    quiz_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
):
    """Get ranked leaderboard for a quiz (instructor only)."""
    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id, Quiz.instructor_id == current_user.id)
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    return get_quiz_leaderboard(quiz_id, db)


@router.get("/me", response_model=StudentAnalytics)
def my_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get personal performance analytics for the current user."""
    return get_student_analytics(current_user, db)


@router.get("/platform", response_model=PlatformSummary)
def platform_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get platform-wide summary statistics."""
    return get_platform_summary(db)
