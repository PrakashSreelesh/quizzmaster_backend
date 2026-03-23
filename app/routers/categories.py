from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Category
from app.schemas import CategoryOut, CategoryCreate, GenericResponse
from app.core.dependencies import get_current_instructor, get_current_user

router = APIRouter()

@router.get("/", response_model=GenericResponse[List[CategoryOut]])
def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all available categories."""
    categories = db.query(Category).order_by(Category.name.asc()).all()
    return GenericResponse(data=categories)

@router.post("/", response_model=GenericResponse[CategoryOut], status_code=status.HTTP_201_CREATED)
def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_instructor),
):
    """Create a new category (instructor only)."""
    # Check if exists
    existing = db.query(Category).filter(Category.name == category_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    
    category = Category(name=category_data.name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return GenericResponse(data=category, message="Category created successfully")
