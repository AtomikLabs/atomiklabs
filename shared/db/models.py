#!/usr/bin/env python3
"""
SQLAlchemy ORM models for the arXiv data layer.

These models correspond to the Pydantic schema models but are used
for database interaction via SQLAlchemy.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, Integer, 
    ForeignKey, UniqueConstraint, Index, Table
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Base class for all models
Base = declarative_base()

class ArxivSet(Base):
    """Model representing an arXiv set (e.g., cs, physics, math)"""
    __tablename__ = 'arxiv_sets'
    
    set_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    set_code = Column(String(20), nullable=False, unique=True, index=True)
    set_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    
    # Relationships
    categories = relationship("Category", back_populates="arxiv_set")
    ingestion_logs = relationship("IngestionLog", back_populates="arxiv_set")
    
    def __repr__(self):
        return f"<ArxivSet(set_code='{self.set_code}', set_name='{self.set_name}')>"


class Category(Base):
    """Model representing an arXiv category"""
    __tablename__ = 'categories'
    
    category_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    set_id = Column(UUID(as_uuid=True), ForeignKey('arxiv_sets.set_id'), nullable=False)
    category_code = Column(String(10), nullable=False, index=True)
    category_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    
    # Unique constraint on set_id + category_code
    __table_args__ = (
        UniqueConstraint('set_id', 'category_code', name='uix_category_set_code'),
    )
    
    # Relationships
    arxiv_set = relationship("ArxivSet", back_populates="categories")
    paper_categories = relationship("PaperCategory", back_populates="category")
    
    def __repr__(self):
        return f"<Category(category_code='{self.category_code}', category_name='{self.category_name}')>"


class Author(Base):
    """Model representing a paper author"""
    __tablename__ = 'authors'
    
    author_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    
    # Index on last_name for faster author searches
    __table_args__ = (
        Index('idx_author_last_name', last_name),
    )
    
    # Relationships
    paper_authors = relationship("PaperAuthor", back_populates="author")
    author_affiliations = relationship("AuthorAffiliation", back_populates="author")
    
    def __repr__(self):
        return f"<Author(first_name='{self.first_name}', last_name='{self.last_name}')>"


class Affiliation(Base):
    """Model representing an author's affiliation"""
    __tablename__ = 'affiliations'
    
    affiliation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_name = Column(String(200), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    
    # Relationships
    author_affiliations = relationship("AuthorAffiliation", back_populates="affiliation")
    
    def __repr__(self):
        return f"<Affiliation(institution_name='{self.institution_name}')>"


class Paper(Base):
    """Model representing an arXiv paper"""
    __tablename__ = 'papers'
    
    paper_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    arxiv_identifier = Column(String(20), nullable=False, unique=True, index=True)
    title = Column(String(500), nullable=False)
    abstract_preview = Column(String(150), nullable=True)
    publication_date = Column(DateTime, nullable=False, index=True)
    full_abstract_s3_key = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    
    # Relationships
    paper_authors = relationship("PaperAuthor", back_populates="paper")
    paper_categories = relationship("PaperCategory", back_populates="paper")
    
    def __repr__(self):
        return f"<Paper(arxiv_identifier='{self.arxiv_identifier}', title='{self.title[:50]}...')>"


class PaperAuthor(Base):
    """Model representing the link between a paper and an author"""
    __tablename__ = 'paper_authors'
    
    paper_author_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey('papers.paper_id'), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey('authors.author_id'), nullable=False)
    author_position = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Unique constraint and indexes
    __table_args__ = (
        UniqueConstraint('paper_id', 'author_id', name='uix_paper_author'),
        Index('idx_paper_author_paper_id', paper_id),
        Index('idx_paper_author_author_id', author_id),
    )
    
    # Relationships
    paper = relationship("Paper", back_populates="paper_authors")
    author = relationship("Author", back_populates="paper_authors")
    
    def __repr__(self):
        return f"<PaperAuthor(paper_id='{self.paper_id}', author_id='{self.author_id}', position={self.author_position})>"


class PaperCategory(Base):
    """Model representing the link between a paper and a category"""
    __tablename__ = 'paper_categories'
    
    paper_category_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey('papers.paper_id'), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey('categories.category_id'), nullable=False)
    is_primary = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Unique constraint and indexes
    __table_args__ = (
        UniqueConstraint('paper_id', 'category_id', name='uix_paper_category'),
        Index('idx_paper_category_paper_id', paper_id),
        Index('idx_paper_category_category_id', category_id),
    )
    
    # Relationships
    paper = relationship("Paper", back_populates="paper_categories")
    category = relationship("Category", back_populates="paper_categories")
    
    def __repr__(self):
        return f"<PaperCategory(paper_id='{self.paper_id}', category_id='{self.category_id}', is_primary={self.is_primary})>"


class AuthorAffiliation(Base):
    """Model representing the link between an author and affiliation for a paper"""
    __tablename__ = 'author_affiliations'
    
    author_affiliation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id = Column(UUID(as_uuid=True), ForeignKey('authors.author_id'), nullable=False)
    affiliation_id = Column(UUID(as_uuid=True), ForeignKey('affiliations.affiliation_id'), nullable=False)
    paper_id = Column(UUID(as_uuid=True), ForeignKey('papers.paper_id'), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_author_affiliation_author_id', author_id),
        Index('idx_author_affiliation_affiliation_id', affiliation_id),
        Index('idx_author_affiliation_paper_id', paper_id),
    )
    
    # Relationships
    author = relationship("Author", back_populates="author_affiliations")
    affiliation = relationship("Affiliation", back_populates="author_affiliations")
    
    def __repr__(self):
        return f"<AuthorAffiliation(author_id='{self.author_id}', affiliation_id='{self.affiliation_id}')>"


class IngestionLog(Base):
    """Model representing an ingestion log entry"""
    __tablename__ = 'ingestion_logs'
    
    ingestion_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String(50), nullable=False)
    set_id = Column(UUID(as_uuid=True), ForeignKey('arxiv_sets.set_id'), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False)
    records_processed = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_ingestion_log_set_id', set_id),
        Index('idx_ingestion_log_status', status),
        Index('idx_ingestion_log_start_time', start_time),
    )
    
    # Relationships
    arxiv_set = relationship("ArxivSet", back_populates="ingestion_logs")
    
    def __repr__(self):
        return f"<IngestionLog(source='{self.source}', status='{self.status}', records_processed={self.records_processed})>" 