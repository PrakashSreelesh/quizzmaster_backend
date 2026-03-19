"""
QuizzMaster Backend - Quizzes Router
Full CRUD for quizzes and questions (instructor).
Published quiz views for students (answers stripped).
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import User, Quiz, Question
from app.schemas import (
    QuizCreate, QuizUpdate, QuizOut, QuizListOut, QuizOutStudent,
    QuestionCreate, QuestionUpdate, QuestionOut,
)
from app.core.dependencies import get_current_user, get_current_instructor, get_current_user_optional

router = APIRouter()


# ─── Helper: strip is_correct from options ───────────────────────────

def strip_correct_answers(options: list) -> list:
    """Remove is_correct from option dicts so students can't see correct answers."""
    if not options:
        return []
    return [
        {k: v for k, v in opt.items() if k != "is_correct"}
        for opt in options
    ]


# ─── Instructor: Quiz CRUD ──────────────────────────────────────────

@router.post("/", response_model=QuizOut, status_code=status.HTTP_201_CREATED)
def create_quiz(
    quiz_data: QuizCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
):
    """Create a new quiz (instructor only)."""
    quiz = Quiz(
        title=quiz_data.title,
        description=quiz_data.description,
        time_limit_minutes=quiz_data.time_limit_minutes,
        instructor_id=current_user.id,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


@router.get("/my", response_model=List[QuizListOut])
def list_my_quizzes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
):
    """List all quizzes created by the current instructor."""
    quizzes = (
        db.query(Quiz)
        .filter(Quiz.instructor_id == current_user.id)
        .options(joinedload(Quiz.questions))
        .order_by(Quiz.created_at.desc())
        .all()
    )
    result = []
    for q in quizzes:
        result.append(QuizListOut(
            id=q.id,
            title=q.title,
            description=q.description,
            is_published=q.is_published,
            time_limit_minutes=q.time_limit_minutes,
            created_at=q.created_at,
            updated_at=q.updated_at,
            question_count=len(q.questions),
            instructor_name=current_user.username,
        ))
    return result


@router.get("/published", response_model=List[QuizListOut])
def list_published_quizzes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """List all published quizzes (any authenticated user)."""
    quizzes = (
        db.query(Quiz)
        .filter(Quiz.is_published == True)
        .options(joinedload(Quiz.questions), joinedload(Quiz.instructor))
        .order_by(Quiz.created_at.desc())
        .all()
    )
    result = []
    for q in quizzes:
        result.append(QuizListOut(
            id=q.id,
            title=q.title,
            description=q.description,
            is_published=q.is_published,
            time_limit_minutes=q.time_limit_minutes,
            created_at=q.created_at,
            updated_at=q.updated_at,
            question_count=len(q.questions),
            instructor_name=q.instructor.username if q.instructor else None,
        ))
    return result


@router.get("/published/{quiz_id}", response_model=QuizOutStudent)
def get_published_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a published quiz with questions (answers stripped for students)."""
    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id, Quiz.is_published == True)
        .options(joinedload(Quiz.questions))
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Published quiz not found")

    # Strip is_correct from options
    quiz_data = QuizOutStudent(
        id=quiz.id,
        title=quiz.title,
        description=quiz.description,
        is_published=quiz.is_published,
        time_limit_minutes=quiz.time_limit_minutes,
        created_at=quiz.created_at,
        question_count=len(quiz.questions),
        questions=[],
    )
    for q in quiz.questions:
        from app.schemas import QuestionOutStudent
        quiz_data.questions.append(QuestionOutStudent(
            id=q.id,
            quiz_id=q.quiz_id,
            text=q.text,
            question_type=q.question_type,
            points=q.points,
            order=q.order,
            options=strip_correct_answers(q.options or []),
        ))

    return quiz_data


@router.get("/{quiz_id}", response_model=QuizOut)
def get_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
):
    """Get a quiz with full details including correct answers (instructor only)."""
    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id, Quiz.instructor_id == current_user.id)
        .options(joinedload(Quiz.questions))
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz


@router.put("/{quiz_id}", response_model=QuizOut)
def update_quiz(
    quiz_id: int,
    quiz_data: QuizUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
):
    """Update quiz metadata (instructor only, must own the quiz)."""
    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id, Quiz.instructor_id == current_user.id)
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    update_data = quiz_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(quiz, field, value)

    db.commit()
    db.refresh(quiz)
    return quiz


@router.delete("/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
):
    """Delete a quiz and all its questions/submissions (instructor only)."""
    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id, Quiz.instructor_id == current_user.id)
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    db.delete(quiz)
    db.commit()
    return None


# ─── Instructor: Question Management ────────────────────────────────

@router.get("/{quiz_id}/questions", response_model=List[QuestionOut])
def list_quiz_questions(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
):
    """List all questions for a quiz (instructor only)."""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.instructor_id == current_user.id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz.questions


@router.post("/{quiz_id}/questions", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
def add_question(
    quiz_id: int,
    question_data: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
):
    """Add a question to a quiz (instructor only)."""
    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id, Quiz.instructor_id == current_user.id)
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    question = Question(
        quiz_id=quiz.id,
        text=question_data.text,
        question_type=question_data.question_type,
        points=question_data.points,
        order=question_data.order,
        options=question_data.options,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.put("/{quiz_id}/questions/{question_id}", response_model=QuestionOut)
def update_question(
    quiz_id: int,
    question_id: int,
    question_data: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
):
    """Update a question (instructor only)."""
    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id, Quiz.instructor_id == current_user.id)
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    question = (
        db.query(Question)
        .filter(Question.id == question_id, Question.quiz_id == quiz_id)
        .first()
    )
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    update_data = question_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(question, field, value)

    db.commit()
    db.refresh(question)
    return question


@router.delete("/{quiz_id}/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(
    quiz_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
):
    """Delete a question from a quiz (instructor only)."""
    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id, Quiz.instructor_id == current_user.id)
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    question = (
        db.query(Question)
        .filter(Question.id == question_id, Question.quiz_id == quiz_id)
        .first()
    )
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    db.delete(question)
    db.commit()
    return None
