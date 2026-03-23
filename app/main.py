"""
QuizzMaster Backend - FastAPI Application Entry Point
Configures CORS, registers routers, and initializes the database on startup.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database import engine, Base
from app.routers import auth, quizzes, submissions, analytics, categories
from app.core.logging_config import logger
import time
from fastapi import Request
import traceback


from app.core.limiter import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

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

app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"success": False, "message": "Too many requests. Please try again later.", "error": str(exc.detail)}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": str(exc.detail),
            "error": getattr(exc, "error", None)
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Validation Error",
            "error": exc.errors()
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global Exception: {str(exc)}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal Server Error",
            "error": str(exc) if settings.DEBUG else "Please contact support."
        }
    )

# ─── Logging Middleware ───────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = None
    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        logger.info(
            f"Method: {request.method} Path: {request.url.path} "
            f"Status: {response.status_code} Time: {process_time:.2f}ms"
        )
        return response
    except Exception as e:
        process_time = (time.time() - start_time) * 1000
        logger.error(
            f"Method: {request.method} Path: {request.url.path} "
            f"Error: {str(e)} Time: {process_time:.2f}ms\n"
            f"{traceback.format_exc()}"
        )
        raise e

# ─── CORS Middleware ─────────────────────────────────────────────────
cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
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
app.include_router(
    categories.router,
    prefix=f"{settings.API_V1_PREFIX}/categories",
    tags=["Categories"],
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
