"""
QuizzMaster Backend - FastAPI Dependencies
Authentication and role-based access control dependencies.
"""
from fastapi import Depends, HTTPException, status, Cookie, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import decode_access_token
from app.models import User

# Keep these for Swagger/OpenAPI documentation, but they won't be the primary source for the web app
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    access_token: str | None = Cookie(None),
    token_header: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode JWT from cookie or header, look up user, raise 401 if invalid."""
    token = access_token or token_header
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    # Enforce access token type
    if payload.get("type") != "access":
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    return user


def get_current_instructor(
    current_user: User = Depends(get_current_user),
) -> User:
    """Enforce instructor role."""
    if current_user.role != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instructor access required",
        )
    return current_user


def get_current_student(
    current_user: User = Depends(get_current_user),
) -> User:
    """Enforce student role."""
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access required",
        )
    return current_user


def get_current_user_optional(
    access_token: str | None = Cookie(None),
    token_header: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Decode JWT if present, otherwise return None."""
    token = access_token or token_header
    if not token:
        return None
    try:
        return get_current_user(access_token, token_header, db)
    except HTTPException:
        return None
