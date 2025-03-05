#!/usr/bin/env python3
"""
Database operations for the arXiv data layer.

This module provides standard CRUD operations and common database
queries for all models in the data layer.
"""

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, Generic
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func

from shared.db.connection import db_session
from shared.db.models import Base

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Type variable for model classes
T = TypeVar('T', bound=Base)


def get_item_by_id(model_class: Type[T], item_id: UUID, session: Optional[Session] = None) -> Optional[T]:
    """
    Get a single item by its ID.
    
    Args:
        model_class: The SQLAlchemy model class
        item_id: The UUID of the item to retrieve
        session: Optional database session
        
    Returns:
        The item if found, None otherwise
    """
    try:
        if session:
            return session.query(model_class).filter(model_class.get_id_column() == item_id).first()
        else:
            with db_session() as db:
                return db.query(model_class).filter(model_class.get_id_column() == item_id).first()
    except SQLAlchemyError as e:
        logger.error(f"Error getting {model_class.__name__} with ID {item_id}: {str(e)}")
        raise


def get_items(
    model_class: Type[T], 
    filters: Optional[Dict[str, Any]] = None, 
    page: int = 1, 
    page_size: int = 20,
    sort_by: Optional[str] = None,
    sort_desc: bool = False,
    session: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Get a paginated list of items with optional filtering and sorting.
    
    Args:
        model_class: The SQLAlchemy model class
        filters: Optional dictionary of filter conditions {column_name: value}
        page: Page number (1-indexed)
        page_size: Number of items per page
        sort_by: Column name to sort by
        sort_desc: Whether to sort in descending order
        session: Optional database session
        
    Returns:
        Dictionary with items, total count, and pagination info
    """
    try:
        if session is None:
            with db_session() as session:
                return _get_items_internal(
                    session, model_class, filters, page, page_size, sort_by, sort_desc
                )
        else:
            return _get_items_internal(
                session, model_class, filters, page, page_size, sort_by, sort_desc
            )
    except SQLAlchemyError as e:
        logger.error(f"Error getting {model_class.__name__} items: {str(e)}")
        raise


def _get_items_internal(
    session: Session,
    model_class: Type[T],
    filters: Optional[Dict[str, Any]],
    page: int,
    page_size: int,
    sort_by: Optional[str],
    sort_desc: bool
) -> Dict[str, Any]:
    """Internal implementation of get_items to handle the database query"""
    # Build the base query
    query = session.query(model_class)
    
    # Apply filters if provided
    if filters:
        for column_name, value in filters.items():
            if hasattr(model_class, column_name):
                column = getattr(model_class, column_name)
                query = query.filter(column == value)
    
    # Get total count for pagination
    total_count = query.count()
    
    # Apply sorting if provided
    if sort_by and hasattr(model_class, sort_by):
        sort_column = getattr(model_class, sort_by)
        if sort_desc:
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    items = query.all()
    
    # Calculate total pages
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
    
    return {
        "items": items,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "pages": total_pages
    }


def create_item(model_class: Type[T], data: Dict[str, Any], session: Optional[Session] = None) -> T:
    """
    Create a new item.
    
    Args:
        model_class: The SQLAlchemy model class
        data: Dictionary of column values
        session: Optional database session
        
    Returns:
        The created item
    """
    try:
        item = model_class(**data)
        
        if session:
            session.add(item)
            session.flush()  # Flush to get the ID, but don't commit yet
            return item
        else:
            with db_session() as db:
                db.add(item)
                db.flush()  # Flush to get the ID
                db.commit()
                return item
    except SQLAlchemyError as e:
        logger.error(f"Error creating {model_class.__name__}: {str(e)}")
        raise


def update_item(
    model_class: Type[T], 
    item_id: UUID, 
    data: Dict[str, Any], 
    session: Optional[Session] = None
) -> Optional[T]:
    """
    Update an existing item by ID.
    
    Args:
        model_class: The SQLAlchemy model class
        item_id: The UUID of the item to update
        data: Dictionary of column values to update
        session: Optional database session
        
    Returns:
        The updated item if found, None otherwise
    """
    try:
        if session:
            item = session.query(model_class).filter(model_class.get_id_column() == item_id).first()
            if item:
                for key, value in data.items():
                    if hasattr(item, key):
                        setattr(item, key, value)
                session.flush()
                return item
            return None
        else:
            with db_session() as db:
                item = db.query(model_class).filter(model_class.get_id_column() == item_id).first()
                if item:
                    for key, value in data.items():
                        if hasattr(item, key):
                            setattr(item, key, value)
                    db.commit()
                    return item
                return None
    except SQLAlchemyError as e:
        logger.error(f"Error updating {model_class.__name__} with ID {item_id}: {str(e)}")
        raise


def delete_item(model_class: Type[T], item_id: UUID, session: Optional[Session] = None) -> bool:
    """
    Delete an item by ID.
    
    Args:
        model_class: The SQLAlchemy model class
        item_id: The UUID of the item to delete
        session: Optional database session
        
    Returns:
        True if deleted, False if not found
    """
    try:
        if session:
            item = session.query(model_class).filter(model_class.get_id_column() == item_id).first()
            if item:
                session.delete(item)
                session.flush()
                return True
            return False
        else:
            with db_session() as db:
                item = db.query(model_class).filter(model_class.get_id_column() == item_id).first()
                if item:
                    db.delete(item)
                    db.commit()
                    return True
                return False
    except SQLAlchemyError as e:
        logger.error(f"Error deleting {model_class.__name__} with ID {item_id}: {str(e)}")
        raise


# Add a helper method to Base class to get the ID column
def get_id_column(self):
    """Get the primary key column for the model"""
    primary_key_columns = self.__table__.primary_key.columns
    if primary_key_columns:
        return getattr(self.__class__, list(primary_key_columns)[0].name)
    raise ValueError(f"No primary key found for {self.__class__.__name__}")

# Add the method to the Base class
Base.get_id_column = classmethod(get_id_column) 