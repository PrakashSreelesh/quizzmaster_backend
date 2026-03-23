from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request, Response, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import random
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models import User, UserOTP
from app.schemas import (
    UserCreate, UserOut, Token, OTPVerify, OTPResend, 
    EmailUpdate, GenericResponse, ForgotPasswordRequest, ResetPasswordRequest
)
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_access_token
from app.core.dependencies import get_current_user
from app.services.email_service import send_otp_email, send_password_reset_email
from app.core.config import settings
from app.core.limiter import limiter

router = APIRouter()

@router.post("/register", response_model=GenericResponse[dict], status_code=status.HTTP_201_CREATED)
@limiter.limit("3/hour")
def register(
    request: Request,
    user_data: UserCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Register a new user (inactive) and send OTP."""
    # Check email uniqueness
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check username uniqueness
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role,
        is_active=False  # Explicitly inactive
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate 6-digit OTP
    otp_code = "".join([str(random.randint(0, 9)) for _ in range(6)])
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=20)
    
    otp_entry = UserOTP(
        user_id=new_user.id,
        otp_code=otp_code,
        expires_at=expires_at
    )
    db.add(otp_entry)
    db.commit()

    # Send Email in background
    verification_url = f"{settings.FRONTEND_URL}/auth/verify?user_id={new_user.id}"
    background_tasks.add_task(send_otp_email, new_user.email, otp_code, verification_url)

    return GenericResponse(
        message="Registration successful. Please check your email for the OTP code.",
        data={"user_id": new_user.id, "email": new_user.email}
    )

@router.post("/verify-otp", response_model=GenericResponse[dict])
@limiter.limit("10/hour")
def verify_otp(request: Request, data: OTPVerify, db: Session = Depends(get_db)):
    """Verify OTP and activate user."""
    otp = db.query(UserOTP).filter(
        UserOTP.user_id == data.user_id,
        UserOTP.otp_code == data.otp_code,
        UserOTP.is_used == False
    ).first()

    # Allow OTP Bypass if configured
    is_bypass = settings.OTP_BYPASS and data.otp_code == settings.OTP_BYPASS

    if not otp and not is_bypass:
        raise HTTPException(status_code=400, detail="Invalid OTP code.")
    
    # If using bypass, we need to find ANY active OTP for this user to mark as used, 
    # or just proceed if none exists (but usually one does).
    if is_bypass and not otp:
        otp = db.query(UserOTP).filter(
            UserOTP.user_id == data.user_id,
            UserOTP.is_used == False
        ).order_by(UserOTP.created_at.desc()).first()

    if otp:
        # Ensure comparison is done with aware datetimes
        if otp.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc) and not is_bypass:
            raise HTTPException(status_code=400, detail="OTP code has expired.")

    # Activate user
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    user.is_active = True
    otp.is_used = True
    db.commit()

    return GenericResponse(message="Account verified successfully. You can now login.")

@router.post("/resend-otp", response_model=GenericResponse[dict])
@limiter.limit("5/hour")
def resend_otp(request: Request, data: OTPResend, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Resend OTP if expired."""
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    if user.is_active:
        raise HTTPException(status_code=400, detail="User is already verified.")

    # Generate new OTP
    otp_code = "".join([str(random.randint(0, 9)) for _ in range(6)])
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=20)
    
    otp_entry = UserOTP(
        user_id=user.id,
        otp_code=otp_code,
        expires_at=expires_at
    )
    db.add(otp_entry)
    db.commit()

    verification_url = f"{settings.FRONTEND_URL}/auth/verify?user_id={user.id}"
    background_tasks.add_task(send_otp_email, user.email, otp_code, verification_url)

    return GenericResponse(message="New OTP code sent to your email.")

@router.post("/update-email", response_model=GenericResponse[dict])
def update_email_verification(data: EmailUpdate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Update email and resend OTP if user entered wrong email during signup."""
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    if user.is_active:
        raise HTTPException(status_code=400, detail="Account already verified.")

    # Check if new email is already taken
    if db.query(User).filter(User.email == data.new_email, User.id != data.user_id).first():
        raise HTTPException(status_code=400, detail="Email already in use.")

    user.email = data.new_email
    db.commit()

    # Resend OTP to new email
    return resend_otp(OTPResend(user_id=user.id), background_tasks, db)


# Helper to set cookies
def set_auth_cookies(response: Response, user_id: str, role: str):
    access_token = create_access_token(data={"sub": str(user_id), "role": role})
    refresh_token = create_refresh_token(data={"sub": str(user_id), "role": role})
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        domain=settings.COOKIE_DOMAIN,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        domain=settings.COOKIE_DOMAIN,
    )

@router.post("/login", response_model=GenericResponse[dict])
@limiter.limit("10/minute")
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login with username+password OR email+password, sets HttpOnly cookies."""
    # Check if input is username or email
    user = db.query(User).filter(
        (User.username == form_data.username) | (User.email == form_data.username)
    ).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    set_auth_cookies(response, user.id, user.role)
    
    return GenericResponse(
        message="Login successful",
        data={"user": {"id": user.id, "username": user.username, "role": user.role}}
    )


@router.post("/refresh", response_model=GenericResponse[dict])
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: Session = Depends(get_db)
):
    """Regenerate access token using refresh token."""
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")

    payload = decode_access_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    # Issue rolling cookies
    set_auth_cookies(response, user.id, user.role)
    
    return GenericResponse(message="Token refreshed successfully")


@router.post("/logout", response_model=GenericResponse[dict])
def logout(response: Response):
    """Clear authentication cookies."""
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        domain=settings.COOKIE_DOMAIN,
    )
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        domain=settings.COOKIE_DOMAIN,
    )
    return GenericResponse(message="Logout successful")


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Get the currently authenticated user."""
    return current_user


@router.post("/forgot-password", response_model=GenericResponse[dict])
@limiter.limit("5/hour")
def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Request a password reset OTP."""
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        # For security, don't reveal if user exists. Just say "If an account exists..."
        return GenericResponse(message="If an account with that email exists, an OTP has been sent.")

    # Generate 6-digit OTP
    otp_code = "".join([str(random.randint(0, 9)) for _ in range(6)])
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=20)
    
    otp_entry = UserOTP(
        user_id=user.id,
        otp_code=otp_code,
        expires_at=expires_at
    )
    db.add(otp_entry)
    db.commit()

    # Send Password Reset Email in background
    background_tasks.add_task(send_password_reset_email, user.email, otp_code)

    return GenericResponse(message="A password reset OTP has been sent to your email.")


@router.post("/reset-password", response_model=GenericResponse[dict])
@limiter.limit("10/hour")
def reset_password(request: Request, data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Verify OTP and reset password."""
    # Find active user by email
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Find valid OTP for this user
    otp = db.query(UserOTP).filter(
        UserOTP.user_id == user.id,
        UserOTP.otp_code == data.otp_code,
        UserOTP.is_used == False
    ).first()

    # Allow OTP Bypass if configured
    is_bypass = settings.OTP_BYPASS and data.otp_code == settings.OTP_BYPASS

    if not otp and not is_bypass:
        raise HTTPException(status_code=400, detail="Invalid OTP code.")
    
    # If using bypass, find the latest unused OTP
    if is_bypass and not otp:
        otp = db.query(UserOTP).filter(
            UserOTP.user_id == user.id,
            UserOTP.is_used == False
        ).order_by(UserOTP.created_at.desc()).first()

    if otp:
        # Ensure comparison is done with aware datetimes
        if otp.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc) and not is_bypass:
            raise HTTPException(status_code=400, detail="OTP code has expired.")

    # Update password and mark OTP as used
    user.hashed_password = get_password_hash(data.new_password)
    otp.is_used = True
    db.commit()

    return GenericResponse(message="Password has been reset successfully. You can now login.")
