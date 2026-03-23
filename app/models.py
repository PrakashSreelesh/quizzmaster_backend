import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Text, Float, Boolean, DateTime,
    ForeignKey, JSON, Integer
)
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Category(Base):
    __tablename__ = "categories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # "instructor" or "student"
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    quizzes = relationship("Quiz", back_populates="instructor", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="student", cascade="all, delete-orphan")


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    instructor_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    is_published = Column(Boolean, default=False)
    time_limit_minutes = Column(Integer, nullable=True)  # null = no limit
    max_attempts = Column(Integer, default=1)  # Instructor can set limit
    categories = Column(JSON, default=list)    # e.g. ["IT", "Programming"]
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    instructor = relationship("User", back_populates="quizzes")
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan",
                             order_by="Question.order")
    submissions = relationship("Submission", back_populates="quiz", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quiz_id = Column(String(36), ForeignKey("quizzes.id"), nullable=False)
    text = Column(Text, nullable=False)
    question_type = Column(String(20), nullable=False)  # "multiple_choice", "true_false", "short_answer"
    points = Column(Float, default=1.0)
    order = Column(Integer, default=0)
    options = Column(JSON, nullable=True)  # format depends on question_type

    # Relationships
    quiz = relationship("Quiz", back_populates="questions")
    answers = relationship("Answer", back_populates="question", cascade="all, delete-orphan")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quiz_id = Column(String(36), ForeignKey("quizzes.id"), nullable=False)
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    score = Column(Float, nullable=True)       # null until graded
    max_score = Column(Float, nullable=True)    # null until graded
    percentage = Column(Float, nullable=True)   # null until graded
    submitted_at = Column(DateTime, default=utcnow)
    graded_at = Column(DateTime, nullable=True)

    # Metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    location = Column(String(255), nullable=True)

    # Relationships
    quiz = relationship("Quiz", back_populates="submissions")
    student = relationship("User", back_populates="submissions")
    answers = relationship("Answer", back_populates="submission", cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = Column(String(36), ForeignKey("submissions.id"), nullable=False)
    question_id = Column(String(36), ForeignKey("questions.id"), nullable=False)
    answer_value = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)       # null until graded
    points_awarded = Column(Float, nullable=True)     # null until graded

    # Relationships
    submission = relationship("Submission", back_populates="answers")
    question = relationship("Question", back_populates="answers")


class UserOTP(Base):
    __tablename__ = "user_otps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    otp_code = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", backref="otps")
