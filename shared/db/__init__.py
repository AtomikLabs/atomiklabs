#!/usr/bin/env python3
"""
Database access layer for the arXiv data layer.

This package provides a standardized interface for connecting to and
interacting with the RDS PostgreSQL database across Lambda functions.
"""

# Connection management
from shared.db.connection import (
    get_db_connection,
    close_db_connection,
    db_session
)

# Database operations
from shared.db.operations import (
    get_item_by_id,
    get_items,
    create_item,
    update_item,
    delete_item
)

# Database models
from shared.db.models import (
    Base,
    ArxivSet,
    Category,
    Author,
    Affiliation,
    Paper,
    PaperAuthor,
    PaperCategory,
    AuthorAffiliation,
    IngestionLog
)

# Model converters
from shared.db.converters import (
    to_pydantic,
    to_sqlalchemy,
    paper_to_summary,
    paper_to_detail,
    ingestion_to_summary,
    ingestion_to_detail
)

__all__ = [
    # Connection
    'get_db_connection',
    'close_db_connection',
    'db_session',
    
    # Operations
    'get_item_by_id',
    'get_items',
    'create_item',
    'update_item',
    'delete_item',
    
    # Models
    'Base',
    'ArxivSet',
    'Category',
    'Author',
    'Affiliation',
    'Paper',
    'PaperAuthor',
    'PaperCategory',
    'AuthorAffiliation',
    'IngestionLog',
    
    # Converters
    'to_pydantic',
    'to_sqlalchemy',
    'paper_to_summary',
    'paper_to_detail',
    'ingestion_to_summary',
    'ingestion_to_detail'
] 