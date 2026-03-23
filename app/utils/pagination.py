from typing import List, TypeVar, Generic, Type
from sqlalchemy.orm import Query
from app.schemas import PaginatedResponse, PaginationMeta

T = TypeVar("T")

def paginate(query: Query, page: int, limit: int) -> dict:
    total = query.count()
    totalPages = (total + limit - 1) // limit if limit > 0 else 1
    
    # Apply pagination
    items = query.offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": items,
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": totalPages
        }
    }
