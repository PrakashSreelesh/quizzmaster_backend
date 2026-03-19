"""
QuizzMaster Backend - FastAPI Application Entry Point
Configures CORS, registers routers, and initializes the database on startup.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database import engine, Base
from app.routers import auth, quizzes, submissions, analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="A full-stack online quiz platform for instructors and students.",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS Middleware ─────────────────────────────────────────────────
cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
if settings.DEBUG:
    # In debug mode, we can be more permissive
    if "*" not in cors_origins:
        cors_origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if not settings.DEBUG else ["*"],
    allow_credentials=True if "*" not in cors_origins else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Register Routers ───────────────────────────────────────────────
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["Authentication"],
)
app.include_router(
    quizzes.router,
    prefix=f"{settings.API_V1_PREFIX}/quizzes",
    tags=["Quizzes"],
)
app.include_router(
    submissions.router,
    prefix=f"{settings.API_V1_PREFIX}/submissions",
    tags=["Submissions"],
)
app.include_router(
    analytics.router,
    prefix=f"{settings.API_V1_PREFIX}/analytics",
    tags=["Analytics"],
)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to QuizzMaster API",
        "docs": "/docs",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}
