"""
QuizzMaster Backend - Auth Router
Endpoints: register, login, get current user.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserOut, Token
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.dependencies import get_current_user

router = APIRouter()


import random
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from app.models import UserOTP
from app.schemas import UserCreate, UserOut, Token, OTPVerify, OTPResend, EmailUpdate, GenericResponse
from app.services.email_service import send_otp_email
from app.core.config import settings
from app.core.limiter import limiter
from fastapi import Request

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
    expires_at = datetime.utcnow() + timedelta(minutes=20)
    
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

    if not otp:
        raise HTTPException(status_code=400, detail="Invalid OTP code.")
    
    if otp.expires_at < datetime.utcnow():
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
    expires_at = datetime.utcnow() + timedelta(minutes=20)
    
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


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login with username+password, returns JWT token."""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role}
    )
    return Token(access_token=access_token)


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Get the currently authenticated user."""
    return current_user
