from typing import List, TypeVar, Generic, Type
from sqlalchemy.orm import Query
from app.schemas import PaginatedResponse, PaginationMeta

T = TypeVar("T")

def paginate(query: Query, page: int, size: int) -> dict:
    total = query.count()
    pages = (total + size - 1) // size if size > 0 else 1
    
    # Apply pagination
    items = query.offset((page - 1) * size).limit(size).all()
    
    return {
        "items": items,
        "meta": {
            "total": total,
            "page": page,
            "size": size,
            "pages": pages
        }
    }
