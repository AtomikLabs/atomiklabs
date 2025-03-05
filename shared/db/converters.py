#!/usr/bin/env python3
"""
Converters between Pydantic and SQLAlchemy models for the arXiv data layer.

This module provides utility functions to convert between Pydantic models
(used for API validation) and SQLAlchemy models (used for database interaction).
"""

import logging
from typing import Dict, List, Optional, Type, TypeVar, Union, Any
from uuid import UUID
from datetime import datetime

# Import Pydantic models
from shared.models.schemas import (
    ArxivSet as ArxivSetSchema,
    Category as CategorySchema,
    Author as AuthorSchema,
    Affiliation as AffiliationSchema,
    Paper as PaperSchema,
    PaperAuthor as PaperAuthorSchema,
    PaperCategory as PaperCategorySchema,
    AuthorAffiliation as AuthorAffiliationSchema,
    IngestionLog as IngestionLogSchema,
    PaperSummary,
    AuthorSummary,
    CategorySummary,
    PaperDetail,
    IngestionSummary,
    IngestionDetail
)

# Import SQLAlchemy models
from shared.db.models import (
    ArxivSet as ArxivSetModel,
    Category as CategoryModel,
    Author as AuthorModel,
    Affiliation as AffiliationModel,
    Paper as PaperModel,
    PaperAuthor as PaperAuthorModel,
    PaperCategory as PaperCategoryModel,
    AuthorAffiliation as AuthorAffiliationModel,
    IngestionLog as IngestionLogModel
)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Type variables for models
P = TypeVar('P')  # Pydantic model
S = TypeVar('S')  # SQLAlchemy model


def to_pydantic(db_model: S, pydantic_class: Type[P]) -> P:
    """
    Convert a SQLAlchemy model instance to a Pydantic model instance.
    
    Args:
        db_model: SQLAlchemy model instance
        pydantic_class: Pydantic model class
        
    Returns:
        Pydantic model instance
    """
    # Convert SQLAlchemy model to dict
    data = {c.name: getattr(db_model, c.name) for c in db_model.__table__.columns}
    
    # Create Pydantic model
    return pydantic_class(**data)


def to_sqlalchemy(pydantic_model: P, sqlalchemy_class: Type[S]) -> S:
    """
    Convert a Pydantic model instance to a SQLAlchemy model instance.
    
    Args:
        pydantic_model: Pydantic model instance
        sqlalchemy_class: SQLAlchemy model class
        
    Returns:
        SQLAlchemy model instance
    """
    # Use model_dump() to get a dict of the Pydantic model
    data = pydantic_model.model_dump()
    
    # Filter out any keys not in the SQLAlchemy model
    valid_columns = {c.name for c in sqlalchemy_class.__table__.columns}
    filtered_data = {k: v for k, v in data.items() if k in valid_columns}
    
    # Create SQLAlchemy model
    return sqlalchemy_class(**filtered_data)


def paper_to_summary(paper_model: PaperModel, primary_category: Optional[str] = None) -> PaperSummary:
    """
    Convert a Paper SQLAlchemy model to a PaperSummary Pydantic model.
    
    Args:
        paper_model: Paper SQLAlchemy model
        primary_category: Primary category code if already known
        
    Returns:
        PaperSummary Pydantic model
    """
    if not primary_category:
        # Find the primary category from paper_categories
        for paper_cat in paper_model.paper_categories:
            if paper_cat.is_primary:
                primary_category = paper_cat.category.category_code
                break
    
    return PaperSummary(
        paper_id=paper_model.paper_id,
        arxiv_identifier=paper_model.arxiv_identifier,
        title=paper_model.title,
        abstract_preview=paper_model.abstract_preview,
        publication_date=paper_model.publication_date,
        primary_category=primary_category or "",
        created_at=paper_model.created_at,
        updated_at=paper_model.updated_at
    )


def paper_to_detail(paper_model: PaperModel) -> PaperDetail:
    """
    Convert a Paper SQLAlchemy model to a PaperDetail Pydantic model.
    
    Args:
        paper_model: Paper SQLAlchemy model
        
    Returns:
        PaperDetail Pydantic model
    """
    # Get all authors
    authors = []
    for paper_author in sorted(paper_model.paper_authors, key=lambda pa: pa.author_position):
        authors.append(AuthorSummary(
            author_id=paper_author.author.author_id,
            first_name=paper_author.author.first_name,
            last_name=paper_author.author.last_name
        ))
    
    # Get all categories and find the primary one
    categories = []
    primary_category = None
    for paper_cat in paper_model.paper_categories:
        category = CategorySummary(
            category_id=paper_cat.category.category_id,
            category_code=paper_cat.category.category_code,
            category_name=paper_cat.category.category_name,
            set_code=paper_cat.category.arxiv_set.set_code
        )
        categories.append(category)
        
        if paper_cat.is_primary:
            primary_category = category
    
    # Create abstract URL if we have an S3 key
    abstract_url = None
    if paper_model.full_abstract_s3_key:
        # This would be replaced with actual URL generation
        abstract_url = f"https://example.com/abstracts/{paper_model.arxiv_identifier}"
    
    # Create the PaperDetail
    return PaperDetail(
        paper_id=paper_model.paper_id,
        arxiv_identifier=paper_model.arxiv_identifier,
        title=paper_model.title,
        abstract_preview=paper_model.abstract_preview,
        publication_date=paper_model.publication_date,
        primary_category=primary_category.category_code if primary_category else "",
        authors=authors,
        categories=categories,
        primary_category=primary_category if primary_category else None,
        abstract_url=abstract_url,
        created_at=paper_model.created_at,
        updated_at=paper_model.updated_at
    )


def ingestion_to_summary(ingestion_model: IngestionLogModel) -> IngestionSummary:
    """
    Convert an IngestionLog SQLAlchemy model to an IngestionSummary Pydantic model.
    
    Args:
        ingestion_model: IngestionLog SQLAlchemy model
        
    Returns:
        IngestionSummary Pydantic model
    """
    return IngestionSummary(
        ingestion_id=ingestion_model.ingestion_id,
        set_code=ingestion_model.arxiv_set.set_code,
        start_time=ingestion_model.start_time,
        end_time=ingestion_model.end_time,
        status=ingestion_model.status,
        records_processed=ingestion_model.records_processed,
        created_at=ingestion_model.created_at
    )


def ingestion_to_detail(ingestion_model: IngestionLogModel) -> IngestionDetail:
    """
    Convert an IngestionLog SQLAlchemy model to an IngestionDetail Pydantic model.
    
    Args:
        ingestion_model: IngestionLog SQLAlchemy model
        
    Returns:
        IngestionDetail Pydantic model
    """
    return IngestionDetail(
        ingestion_id=ingestion_model.ingestion_id,
        set_code=ingestion_model.arxiv_set.set_code,
        start_time=ingestion_model.start_time,
        end_time=ingestion_model.end_time,
        status=ingestion_model.status,
        records_processed=ingestion_model.records_processed,
        source=ingestion_model.source,
        error_message=ingestion_model.error_message,
        created_at=ingestion_model.created_at,
        updated_at=ingestion_model.updated_at
    ) 