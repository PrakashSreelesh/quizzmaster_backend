# QuizzMaster — Backend Service

The backend of QuizzMaster is built with **FastAPI**, **SQLAlchemy**, and **PostgreSQL**. It provides a robust REST API for managing quizzes, processing student submissions, and generating analytics.

## 🛠 Tech Stack
- **Framework**: FastAPI
- **Database**: SQLAlchemy (ORM) + Alembic (Migrations)
- **Security**: JWT & Passlib (bcrypt)
- **Testing**: Pytest & Coverage
- **Task Scheduling**: Pydantic for validation

## 🏗 Directory Structure
- `app/`: Main application logic.
  - `core/`: Config, security, and dependencies.
  - `models/`: SQLAlchemy ORM models.
  - `schemas/`: Pydantic V2 models for requests/responses.
  - `routers/`: API route definitions.
  - `services/`: Business logic (grading, analytics).
- `tests/`: Comprehensive test suite.
- `alembic/`: Database migration history.

## 🚀 Local Setup

### Using Docker
The easiest way is to use the root `docker-compose.yml`:
```bash
docker-compose up backend
```

### Manual Run
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Configure `.env` (use `.env.example` as a template).
3. Run migrations:
   ```bash
   alembic upgrade head
   ```
4. Start the server:
   ```bash
   uvicorn app.main:app --reload
   ```

## 📄 API Documentation
Visit `http://localhost:8000/docs` for the interactive Swagger UI.

## 🧪 Testing
```bash
pytest --cov=app tests/
```
