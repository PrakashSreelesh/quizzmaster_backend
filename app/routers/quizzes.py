from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File, Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.database import get_db
from app.models import User, Quiz, Question, Category, Submission
from app.schemas import (
    QuizCreate, QuizUpdate, QuizOut, QuizListOut, QuizOutStudent,
    QuestionCreate, QuestionUpdate, QuestionOut, QuestionOutStudent,
    GenericResponse, PaginatedResponse
)
from app.core.dependencies import get_current_user, get_current_instructor
from app.utils.excel_parser import parse_excel_quiz, generate_template_excel
from app.core.jobs import create_job, get_job_status
from app.services.quiz_import import process_quiz_import
from app.utils.pagination import paginate
from app.utils.search import apply_search

router = APIRouter()


def upsert_categories(categories: List[str], db: Session):
    """Ensure categories mentioned in quiz exist in the Category table."""
    if not categories:
        return
    for name in categories:
        # Check if exists (case-insensitive)
        existing = db.query(Category).filter(Category.name.ilike(name)).first()
        if not existing:
            db.add(Category(name=name))
    db.flush()


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
        max_attempts=quiz_data.max_attempts,
        categories=quiz_data.categories,
        instructor_id=current_user.id,
    )
    db.add(quiz)
    upsert_categories(quiz_data.categories, db)
    db.commit()
    db.refresh(quiz)
    return quiz



# ─── Instructor: Quiz List ──────────────────────────────────────────

@router.get("/my", response_model=GenericResponse[PaginatedResponse[QuizListOut]])
def list_my_quizzes(
    search: str = None,
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
):
    """List all quizzes created by the current instructor with search and pagination."""
    query = db.query(Quiz).filter(Quiz.instructor_id == current_user.id)
    
    # Generic Search
    query = apply_search(query, Quiz, search, ["title", "description"])
    
    query = query.order_by(Quiz.created_at.desc())
    
    # Standard Pagination
    pagination_result = paginate(query, page, limit)
    quizzes = pagination_result["items"]

    items = []
    for q in quizzes:
        stats = (
            db.query(
                func.count(Submission.id).label("count"),
                func.avg(Submission.percentage).label("avg")
            )
            .filter(Submission.quiz_id == q.id, Submission.graded_at.isnot(None))
            .first()
        )

        items.append(QuizListOut(
            id=q.id,
            title=q.title,
            description=q.description,
            is_published=q.is_published,
            time_limit_minutes=q.time_limit_minutes,
            max_attempts=q.max_attempts,
            categories=q.categories or [],
            created_at=q.created_at,
            updated_at=q.updated_at,
            question_count=len(q.questions),
            submission_count=stats.count or 0,
            average_score=round(float(stats.avg or 0), 1),
            instructor_name=current_user.username,
            user_attempts=0,
        ))

    return GenericResponse(data={
        "items": items,
        "pagination": pagination_result["pagination"]
    })


@router.get("/published", response_model=GenericResponse[PaginatedResponse[QuizListOut]])
def list_published_quizzes(
    category: str = None,
    search: str = None,
    page: int = 1,
    limit: int = 12,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all published quizzes with search and pagination."""
    query = (
        db.query(Quiz)
        .filter(Quiz.is_published == True)
        .options(joinedload(Quiz.questions), joinedload(Quiz.instructor))
    )
    
    # Generic Search
    query = apply_search(query, Quiz, search, ["title", "description"])

    # Category Filter
    if category:
        # Search for the category within the JSON array
        query = query.filter(Quiz.categories.ilike(f'%"{category}"%'))
        
    query = query.order_by(Quiz.created_at.desc())
    
    # Standard Pagination
    pagination_result = paginate(query, page, limit)
    quizzes = pagination_result["items"]

    items = []
    from app.models import Submission
    for q in quizzes:
        user_attempts = 0
        if current_user:
            user_attempts = db.query(Submission).filter(
                Submission.quiz_id == q.id, 
                Submission.student_id == current_user.id
            ).count()

        items.append(QuizListOut(
            id=q.id,
            title=q.title,
            description=q.description,
            is_published=q.is_published,
            time_limit_minutes=q.time_limit_minutes,
            max_attempts=q.max_attempts,
            categories=q.categories or [],
            created_at=q.created_at,
            updated_at=q.updated_at,
            question_count=len(q.questions),
            instructor_name=q.instructor.username if q.instructor else None,
            user_attempts=user_attempts,
        ))
    
    return GenericResponse(data={
        "items": items,
        "pagination": pagination_result["pagination"]
    })


@router.get("/published/{quiz_id}", response_model=GenericResponse[QuizOutStudent])
def get_published_quiz(
    quiz_id: str,
    shuffle: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a published quiz with questions (answers stripped for students)."""
    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id, Quiz.is_published == True)
        .options(joinedload(Quiz.questions), joinedload(Quiz.instructor))
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Published quiz not found")
    user_attempts = db.query(Submission).filter(
        Submission.quiz_id == quiz_id, 
        Submission.student_id == current_user.id
    ).count()

    # Strip is_correct from options
    quiz_data = QuizOutStudent(
        id=quiz.id,
        title=quiz.title,
        description=quiz.description,
        is_published=quiz.is_published,
        time_limit_minutes=quiz.time_limit_minutes,
        max_attempts=quiz.max_attempts,
        categories=quiz.categories or [],
        created_at=quiz.created_at,
        question_count=len(quiz.questions),
        questions=[],
        instructor_name=quiz.instructor.username if quiz.instructor else None,
        user_attempts=user_attempts,
    )
    
    questions_list = list(quiz.questions)
    if shuffle:
        import random
        random.shuffle(questions_list)

    for q in questions_list:
        quiz_data.questions.append(QuestionOutStudent(
            id=q.id,
            quiz_id=q.quiz_id,
            text=q.text,
            question_type=q.question_type,
            points=q.points,
            order=q.order,
            options=strip_correct_answers(q.options or []),
        ))

    return GenericResponse(data=quiz_data)


@router.get("/{quiz_id}", response_model=QuizOut)
def get_quiz(
    quiz_id: str,
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
    quiz_id: str,
    quiz_data: QuizUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
):
    """Update quiz metadata (instructor only, must own the quiz)."""
    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id, Quiz.instructor_id == current_user.id)
        .options(joinedload(Quiz.questions)) # Load questions for validation
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Validation: Cannot publish if no questions
    if quiz_data.is_published is True and len(quiz.questions) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish a quiz with no questions."
        )

    update_data = quiz_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(quiz, field, value)

    if quiz_data.categories is not None:
        upsert_categories(quiz_data.categories, db)

    db.commit()
    db.refresh(quiz)
    return quiz


@router.delete("/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quiz(
    quiz_id: str,
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
    quiz_id: str,
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
    quiz_id: str,
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
    quiz_id: str,
    question_id: str,
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
    quiz_id: str,
    question_id: str,
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


# ─── Excel Import Endpoints ──────────────────────────────────────────

@router.get("/import/template")
def get_import_template():
    """Download Sample Excel Template."""
    template_data = generate_template_excel()
    return Response(
        content=template_data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=quiz_template.xlsx"}
    )


@router.post("/import", status_code=status.HTTP_202_ACCEPTED)
async def import_quiz_from_excel(
    background_tasks: BackgroundTasks,
    title: str,
    description: str = "",
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
):
    """
    Import questions from Excel. 
    Returns a job_id for progress polling.
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are supported")

    content = await file.read()
    questions_data, errors = parse_excel_quiz(content)
    
    # If the file itself is unreadable or missing columns
    if not questions_data and errors:
        raise HTTPException(status_code=400, detail=errors[0])

    # Create the Quiz skeleton first
    quiz = Quiz(
        title=title,
        description=description,
        instructor_id=current_user.id,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    # Initialize the job
    job_id = create_job(len(questions_data), quiz.id)
    
    # Add prepopulated errors from the parser (e.g. invalid rows)
    from app.core.jobs import update_job_progress
    for err in errors:
        update_job_progress(job_id, 0, error=err)

    # Trigger background processing
    background_tasks.add_task(process_quiz_import, job_id, quiz.id, questions_data)

    return {"job_id": job_id, "quiz_id": quiz.id}


@router.get("/import/status/{job_id}")
def get_import_status(
    job_id: str,
    current_user: User = Depends(get_current_instructor),
):
    """Poll for import job status/progress."""
    status_data = get_job_status(job_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Job not found")
    return status_data
