"""
QuizzMaster Backend - Application Configuration
Uses pydantic-settings to load config from environment variables / .env file.
"""
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "QuizzMaster Online Quiz Platform"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "change-me-to-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 180  # 3 hours
    COOKIE_SECURE: bool = False  # Set to True in production (HTTPS)
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: str | None = None
    DATABASE_URL: str = "sqlite:///./quiz_platform.db"
    CORS_ORIGINS: str = "http://localhost:3000"
    FRONTEND_URL: str = "http://localhost:3000"
    OTP_BYPASS: str | None = None

    # SMTP Settings
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_TLS: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
