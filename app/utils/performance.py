"""Performance optimization utilities for database queries and responses"""

from fastapi import Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Any, Optional


class PaginationParams:
    """Standard pagination parameters for list endpoints"""
    
    def __init__(self, skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
        self.skip = skip
        self.limit = limit


def paginate_query(db: Session, query_obj: Any, skip: int = 0, limit: int = 20):
    """
    Apply pagination to a SQLAlchemy query
    
    Args:
        db: Database session
        query_obj: SQLAlchemy query object
        skip: Number of records to skip
        limit: Number of records to return (max 100)
    
    Returns:
        Tuple of (items, total_count)
    """
    limit = min(limit, 100)  # Cap at 100 to prevent abuse
    total_count = db.query(func.count(query_obj)).scalar() or 0
    items = query_obj.offset(skip).limit(limit).all()
    return items, total_count


def add_pagination_headers(response: dict, skip: int = 0, limit: int = 20, total: int = 0):
    """
    Add pagination info to response headers
    
    Args:
        response: Response headers dict
        skip: Offset used
        limit: Limit used
        total: Total count
    """
    response["X-Total-Count"] = str(total)
    response["X-Page-Number"] = str(skip // limit + 1)
    response["X-Page-Size"] = str(limit)
    response["X-Has-More"] = str((skip + limit) < total)
    return response


class QueryOptimizer:
    """Helper class for common query optimizations"""
    
    @staticmethod
    def select_with_limit(query, limit: int = 100):
        """Apply reasonable limit to prevent memory exhaustion"""
        return query.limit(min(limit, 100))
    
    @staticmethod
    def select_columns(query, *columns):
        """Select only specific columns to reduce data transfer"""
        return query.with_entities(*columns)
    
    @staticmethod
    def eager_load(query, *relationships):
        """Eagerly load relationships to prevent N+1 queries"""
        from sqlalchemy.orm import joinedload
        for rel in relationships:
            query = query.options(joinedload(rel))
        return query
