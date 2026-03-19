"""
QuizzMaster Test Configuration
Fixtures for database, client, users, tokens, and sample data.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, get_db
from app.models import User, Quiz, Question
from app.core.security import get_password_hash

# In-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create fresh database tables for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """TestClient with DB dependency override."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def instructor_user(db):
    """Create an instructor user in the DB."""
    user = User(
        email="instructor@test.com",
        username="instructor1",
        hashed_password=get_password_hash("password123"),
        role="instructor",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def student_user(db):
    """Create a student user in the DB."""
    user = User(
        email="student@test.com",
        username="student1",
        hashed_password=get_password_hash("password123"),
        role="student",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def second_student(db):
    """Create a second student user."""
    user = User(
        email="student2@test.com",
        username="student2",
        hashed_password=get_password_hash("password123"),
        role="student",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def instructor_token(client, instructor_user):
    """Login as instructor, return JWT token."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "instructor1", "password": "password123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def student_token(client, student_user):
    """Login as student, return JWT token."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "student1", "password": "password123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def second_student_token(client, second_student):
    """Login as second student, return JWT token."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "student2", "password": "password123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def instructor_headers(instructor_token):
    """Auth headers for instructor."""
    return {"Authorization": f"Bearer {instructor_token}"}


@pytest.fixture
def student_headers(student_token):
    """Auth headers for student."""
    return {"Authorization": f"Bearer {student_token}"}


@pytest.fixture
def second_student_headers(second_student_token):
    """Auth headers for second student."""
    return {"Authorization": f"Bearer {second_student_token}"}


@pytest.fixture
def sample_quiz(db, instructor_user):
    """Create an unpublished quiz with 3 questions."""
    quiz = Quiz(
        title="Python Basics Quiz",
        description="Test your Python knowledge",
        instructor_id=instructor_user.id,
        time_limit_minutes=30,
    )
    db.add(quiz)
    db.flush()

    # Q1: multiple_choice, 1pt — correct answer: "b"
    q1 = Question(
        quiz_id=quiz.id,
        text="What does len() return?",
        question_type="multiple_choice",
        points=1.0,
        order=0,
        options=[
            {"id": "a", "text": "The last element", "is_correct": False},
            {"id": "b", "text": "The number of items", "is_correct": True},
            {"id": "c", "text": "The first element", "is_correct": False},
        ],
    )
    # Q2: true_false, 1pt — correct: "true"
    q2 = Question(
        quiz_id=quiz.id,
        text="Python is a compiled language.",
        question_type="true_false",
        points=1.0,
        order=1,
        options=[
            {"id": "true", "text": "True", "is_correct": False},
            {"id": "false", "text": "False", "is_correct": True},
        ],
    )
    # Q3: short_answer, 2pts — correct: "Paris"
    q3 = Question(
        quiz_id=quiz.id,
        text="What is the capital of France?",
        question_type="short_answer",
        points=2.0,
        order=2,
        options=[
            {"text": "Paris"},
            {"text": "paris"},
        ],
    )
    db.add_all([q1, q2, q3])
    db.commit()
    db.refresh(quiz)
    return quiz


@pytest.fixture
def published_quiz(db, sample_quiz):
    """Same quiz but published."""
    sample_quiz.is_published = True
    db.commit()
    db.refresh(sample_quiz)
    return sample_quiz
