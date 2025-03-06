#!/usr/bin/env python3
"""
Shared Pydantic models for arXiv data processing

These models are used for validation and serialization/deserialization
across different services (ECS, Lambda, API Gateway).
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class ArxivSet(BaseModel):
    """Model representing an arXiv set (e.g., cs, physics, math)"""
    set_id: UUID = Field(default_factory=uuid4)
    set_code: str = Field(min_length=1, max_length=20)
    set_name: str = Field(min_length=1, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Category(BaseModel):
    """Model representing an arXiv category"""
    category_id: UUID = Field(default_factory=uuid4)
    set_id: UUID
    category_code: str = Field(min_length=1, max_length=10)
    category_name: str = Field(min_length=1, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Author(BaseModel):
    """Model representing a paper author"""
    author_id: UUID = Field(default_factory=uuid4)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Affiliation(BaseModel):
    """Model representing an author's affiliation"""
    affiliation_id: UUID = Field(default_factory=uuid4)
    institution_name: str = Field(min_length=1, max_length=200)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class AuthorAffiliation(BaseModel):
    """Model representing the link between an author and affiliation for a paper"""
    author_affiliation_id: UUID = Field(default_factory=uuid4)
    author_id: UUID
    affiliation_id: UUID
    paper_id: Optional[UUID] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PaperAuthor(BaseModel):
    """Model representing the link between a paper and an author"""
    paper_author_id: UUID = Field(default_factory=uuid4)
    paper_id: UUID
    author_id: UUID
    author_position: int = Field(ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PaperCategory(BaseModel):
    """Model representing the link between a paper and a category"""
    paper_category_id: UUID = Field(default_factory=uuid4)
    paper_id: UUID
    category_id: UUID
    is_primary: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Paper(BaseModel):
    """Model representing an arXiv paper"""
    paper_id: UUID = Field(default_factory=uuid4)
    arxiv_identifier: str = Field(min_length=1, max_length=20)
    title: str = Field(min_length=1, max_length=500)
    abstract_preview: Optional[str] = Field(None, max_length=150)
    publication_date: datetime
    full_abstract_s3_key: Optional[str] = Field(None, max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class IngestionStatus(str, Enum):
    """Status of an ingestion job"""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestionLog(BaseModel):
    """Model representing an ingestion log entry"""
    ingestion_id: UUID = Field(default_factory=uuid4)
    source: str = Field(min_length=1, max_length=50)
    set_id: UUID
    start_time: datetime
    end_time: Optional[datetime] = None
    status: IngestionStatus = IngestionStatus.IN_PROGRESS
    records_processed: int = 0
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


# API Request/Response Models

class PaperSearchRequest(BaseModel):
    """Model representing a paper search request"""
    query: Optional[str] = None
    category: Optional[str] = None
    author: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    set_code: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class PaperSummary(BaseModel):
    """Model representing a paper summary for list responses"""
    paper_id: UUID
    arxiv_identifier: str
    title: str
    abstract_preview: Optional[str] = None
    publication_date: datetime
    primary_category: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class AuthorSummary(BaseModel):
    """Model representing an author summary"""
    author_id: UUID
    first_name: str
    last_name: str


class CategorySummary(BaseModel):
    """Model representing a category summary"""
    category_id: UUID
    category_code: str
    category_name: str
    set_code: str


class PaginatedResponse(BaseModel):
    """Generic paginated response model"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int


class PaginatedPapers(PaginatedResponse):
    """Paginated response specifically for papers"""
    items: List[PaperSummary]


class PaginatedAuthors(PaginatedResponse):
    """Paginated response specifically for authors"""
    items: List[AuthorSummary]


class PaginatedCategories(PaginatedResponse):
    """Paginated response specifically for categories"""
    items: List[CategorySummary]


class PaperDetail(PaperSummary):
    """Detailed paper model including authors and categories"""
    authors: List[AuthorSummary]
    categories: List[CategorySummary]
    primary_category: CategorySummary
    abstract_url: Optional[HttpUrl] = None


class StartIngestionRequest(BaseModel):
    """Request model for starting an ingestion job"""
    set_code: str
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    max_records: Optional[int] = Field(None, gt=0, le=10000)


class IngestionSummary(BaseModel):
    """Summary of an ingestion job"""
    ingestion_id: UUID
    set_code: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: IngestionStatus
    records_processed: int
    created_at: datetime


class IngestionDetail(IngestionSummary):
    """Detailed ingestion information"""
    source: str
    error_message: Optional[str] = None
    updated_at: Optional[datetime] = None


class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str
    details: Optional[Dict[str, Any]] = None
