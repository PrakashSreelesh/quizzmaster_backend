# QuizzMaster Backend 🚀

The high-performance API powering the QuizzMaster platform, built with **FastAPI**, **SQLAlchemy**, and **SQLite**.

## 📖 Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Authentication](#authentication)
- [Business Flows](#business-flows)
- [Configuration](#configuration)
- [Local Development](#local-development)
- [Docker & Deployment](#docker--deployment)
- [API Documentation](#api-documentation)

---

## 🔍 Overview
QuizzMaster's backend handles quiz creation, automated question generation via Excel imports, student attempts, and real-time grading. It is designed to be lightweight, secure, and easily scalable.

## 🏗 Architecture
- **Framework**: FastAPI (Asynchronous Python)
- **Database**: SQLite (Development) / PostgreSQL (Production ready)
- **ORM**: SQLAlchemy 2.0 with Alembic migrations
- **Models**:
  - `User`: Handles identity and RBAC (Instructor vs Student).
  - `Quiz`: Core entity for quiz metadata and settings.
  - `Question`: Multiple choice, True/False, and Short answer types.
  - `Submission`: Tracks student attempts and grading results.

## 🔐 Authentication
The system uses a **Secure Cookie-based JWT Authentication** flow:
- **HttpOnly Cookies**: Both `access_token` and `refresh_token` are stored in `HttpOnly`, `SameSite: Lax` cookies to mitigate XSS and CSRF risks.
- **Short-lived Access**: Tokens expire in 15 minutes.
- **Rolling Sessions**: `refresh_token` lasts 3 hours and issues a new pair on use, extending the user's active session seamlessly.
- **RBAC**: Fine-grained access control using FastAPI dependencies (`get_current_instructor`, `get_current_user`).

## 🔄 Business Flows
### 👨‍🏫 Instructor Flow
1. **Manual Creation**: Create quiz metadata -> Add/Edit questions individually.
2. **Bulk Import**: Upload `.xlsx` template -> Background processing -> Review generated quiz.
3. **Analytics**: Monitor student progress through aggregated submission stats.

### 🎓 Student Flow
1. **Discovery**: Browse published quizzes by category or search.
2. **Engagement**: Start attempt -> Auto-save progress -> Instant grading upon submission.
3. **Progress**: View personal history and performance analytics.

## ⚙️ Configuration
Environment variables can be set in a `.env` file within the `backend/` directory:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Secret for JWT signing | `change-me` |
| `ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifespan | `15` |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | Refresh token lifespan | `180` |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///./quiz_platform.db` |
| `CORS_ORIGINS` | Allowed frontend origins | `http://localhost:3000` |
| `DEBUG` | Verbose logging mode | `false` |
| `SMTP_HOST` | SMTP server host | `None` |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USER` | SMTP username | `None` |
| `SMTP_PASSWORD` | SMTP password | `None` |
| `EMAILS_FROM_EMAIL` | Sender email address | `info@quizzmaster.com` |

## 💻 Local Development
1. **Environment Setup**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\\Scripts\\activate
   pip install -r requirements.txt
   ```
2. **Migrations**:
   ```bash
   alembic upgrade head
   ```
3. **Run Server**:
   ```bash
   uvicorn app.main:app --reload
   ```

## 🐳 Docker & Deployment
### Running with Docker Compose
The easiest way to run the entire stack is from the root directory:
```bash
docker-compose up --build
```

### Manual Docker Build
```bash
docker build -t quizzmaster-backend:latest .
docker run -p 8000:8000 --env-file .env quizzmaster-backend:latest
```

### CI/CD & Image Tags
Images are automatically tagged based on GitHub branches:
- `main`: `quizzmaster-backend:latest`
- Tags: `quizzmaster-backend:v1.x.x`

## 📚 API Documentation
Once the server is running, interactive docs are available at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
