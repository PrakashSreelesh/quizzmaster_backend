from sqlalchemy import or_, inspect
from sqlalchemy.orm import Query

def apply_search(query: Query, model, search_query: str, search_fields: list) -> Query:
    """
    Apply case-insensitive search to a SQLAlchemy query.
    
    :param query: The original query
    :param model: The SQLAlchemy model class
    :param search_query: The search string
    :param search_fields: List of field names (as strings) to search in
    """
    if not search_query or not search_fields:
        return query
    
    filters = []
    for field in search_fields:
        attr = getattr(model, field, None)
        if attr:
            filters.append(attr.ilike(f"%{search_query}%"))
            
    if filters:
        return query.filter(or_(*filters))
    
    return query
