"""
QuizzMaster Backend - Pydantic Schemas
Request/response models for all API endpoints.
"""
from datetime import datetime
from typing import List, Optional, Any

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


# ─── Auth / User Schemas ─────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    role: str  # "instructor" or "student"

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("instructor", "student"):
            raise ValueError("Role must be 'instructor' or 'student'")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None


# ─── Question Schemas ────────────────────────────────────────────────

class QuestionCreate(BaseModel):
    text: str
    question_type: str  # "multiple_choice", "true_false", "short_answer"
    points: float = 1.0
    order: int = 0
    options: List[dict] = []

    @field_validator("question_type")
    @classmethod
    def validate_question_type(cls, v: str) -> str:
        valid_types = ("multiple_choice", "true_false", "short_answer")
        if v not in valid_types:
            raise ValueError(f"Question type must be one of: {', '.join(valid_types)}")
        return v


class QuestionUpdate(BaseModel):
    text: Optional[str] = None
    question_type: Optional[str] = None
    points: Optional[float] = None
    order: Optional[int] = None
    options: Optional[List[dict]] = None

    @field_validator("question_type")
    @classmethod
    def validate_question_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_types = ("multiple_choice", "true_false", "short_answer")
            if v not in valid_types:
                raise ValueError(f"Question type must be one of: {', '.join(valid_types)}")
        return v


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_id: int
    text: str
    question_type: str
    points: float
    order: int
    options: Optional[List[dict]] = []


class QuestionOutStudent(BaseModel):
    """Question view for students — is_correct stripped from options."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_id: int
    text: str
    question_type: str
    points: float
    order: int
    options: Optional[List[dict]] = []


# ─── Quiz Schemas ────────────────────────────────────────────────────

class QuizCreate(BaseModel):
    title: str
    description: str = ""
    time_limit_minutes: Optional[int] = None


class QuizUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_published: Optional[bool] = None
    time_limit_minutes: Optional[int] = None


class QuizOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    instructor_id: int
    is_published: bool
    time_limit_minutes: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    questions: List[QuestionOut] = []
    question_count: Optional[int] = None


class QuizOutStudent(BaseModel):
    """Quiz view for students — questions have is_correct stripped."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    is_published: bool
    time_limit_minutes: Optional[int]
    created_at: datetime
    questions: List[QuestionOutStudent] = []
    question_count: Optional[int] = None


class QuizListOut(BaseModel):
    """Lightweight quiz for list views."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    is_published: bool
    time_limit_minutes: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    question_count: int = 0
    instructor_name: Optional[str] = None


# ─── Submission / Answer Schemas ─────────────────────────────────────

class AnswerCreate(BaseModel):
    question_id: int
    answer_value: Optional[str] = None


class SubmissionCreate(BaseModel):
    answers: List[AnswerCreate]


class AnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    answer_value: Optional[str]
    is_correct: Optional[bool]
    points_awarded: Optional[float]


class AnswerDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    answer_value: Optional[str]
    is_correct: Optional[bool]
    points_awarded: Optional[float]
    question_text: Optional[str] = None
    correct_answer: Optional[str] = None


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_id: int
    student_id: int
    score: Optional[float]
    max_score: Optional[float]
    percentage: Optional[float]
    submitted_at: datetime
    graded_at: Optional[datetime]
    answers: List[AnswerOut] = []


class SubmissionDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_id: int
    student_id: int
    score: Optional[float]
    max_score: Optional[float]
    percentage: Optional[float]
    submitted_at: datetime
    graded_at: Optional[datetime]
    answers: List[AnswerDetailOut] = []
    quiz_title: Optional[str] = None
    student_name: Optional[str] = None


# ─── Analytics Schemas ───────────────────────────────────────────────

class QuestionStat(BaseModel):
    question_id: int
    question_text: str
    total_answers: int
    correct_answers: int
    correct_rate: float


class QuizAnalytics(BaseModel):
    quiz_id: int
    quiz_title: str
    total_submissions: int
    average_score: float
    average_percentage: float
    highest_score: float
    lowest_score: float
    pass_rate: float  # percentage >= 60
    question_stats: List[QuestionStat] = []


class LeaderboardEntry(BaseModel):
    rank: int
    student_id: int
    student_name: str
    score: float
    percentage: float
    submitted_at: datetime


class RecentSubmission(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quiz_id: int
    quiz_title: str
    score: float
    max_score: float
    percentage: float
    submitted_at: datetime


class StudentAnalytics(BaseModel):
    total_submissions: int
    average_percentage: float
    quizzes_passed: int
    quizzes_failed: int
    recent_submissions: List[RecentSubmission] = []


class PlatformSummary(BaseModel):
    total_quizzes: int
    total_published_quizzes: int
    total_submissions: int
    total_students: int
    total_instructors: int
    overall_pass_rate: float
