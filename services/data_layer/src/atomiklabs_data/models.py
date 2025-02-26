"""
Database models for the AtomikLabs research data system.
"""

import datetime
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Boolean, ForeignKey, Table, JSON, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Association table for many-to-many relationship between articles and authors
article_authors = Table(
    'article_authors',
    Base.metadata,
    Column('article_id', Integer, ForeignKey('articles.id'), primary_key=True),
    Column('author_id', Integer, ForeignKey('authors.id'), primary_key=True),
    Column('author_order', Integer, nullable=False)
)

# Association table for article categories
article_categories = Table(
    'article_categories',
    Base.metadata,
    Column('article_id', Integer, ForeignKey('articles.id'), primary_key=True),
    Column('category_id', Integer, ForeignKey('categories.id'), primary_key=True),
    Column('is_primary', Boolean, default=False)
)

# Association table for author organizations
author_organizations = Table(
    'author_organizations',
    Base.metadata,
    Column('author_id', Integer, ForeignKey('authors.id'), primary_key=True),
    Column('organization_id', Integer, ForeignKey('organizations.id'), primary_key=True)
)

# Association table for newsletter articles
newsletter_articles = Table(
    'newsletter_articles',
    Base.metadata,
    Column('newsletter_id', Integer, ForeignKey('newsletters.id'), primary_key=True),
    Column('article_id', Integer, ForeignKey('articles.id'), primary_key=True),
    Column('section', String(255)),
    Column('priority', Integer)
)


class Article(Base):
    """Article model representing research papers from various sources."""
    __tablename__ = 'articles'
    
    id = Column(Integer, primary_key=True)
    source_id = Column(String(255), nullable=False)  # e.g., arXiv ID
    source = Column(String(50), nullable=False)      # e.g., "arxiv"
    title = Column(Text, nullable=False)
    publication_date = Column(Date, nullable=False)
    abstract_text = Column(Text)
    s3_abstract_path = Column(String(512))
    s3_fulltext_path = Column(String(512))
    url = Column(String(512))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    authors = relationship("Author", secondary=article_authors, back_populates="articles")
    categories = relationship("Category", secondary=article_categories, back_populates="articles")
    processing_events = relationship("ProcessingEvent", back_populates="article")
    newsletters = relationship("Newsletter", secondary=newsletter_articles, back_populates="articles")
    
    __table_args__ = (
        # Ensure article source_id is unique within a source
        UniqueConstraint('source', 'source_id', name='uq_article_source_id'),
    )


class Author(Base):
    """Author model representing researchers."""
    __tablename__ = 'authors'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    articles = relationship("Article", secondary=article_authors, back_populates="authors")
    organizations = relationship("Organization", secondary=author_organizations, back_populates="authors")


class Organization(Base):
    """Organization model representing research institutions."""
    __tablename__ = 'organizations'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    country = Column(String(255))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    authors = relationship("Author", secondary=author_organizations, back_populates="organizations")


class Category(Base):
    """Category model representing research domains."""
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False, unique=True)
    parent_id = Column(Integer, ForeignKey('categories.id'))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    articles = relationship("Article", secondary=article_categories, back_populates="categories")
    subcategories = relationship("Category", backref=ForeignKey("parent"))


class ProcessingEvent(Base):
    """ProcessingEvent model for tracking data lineage."""
    __tablename__ = 'processing_events'
    
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('articles.id'))
    event_type = Column(String(255), nullable=False)  # e.g., 'ingested', 'processed', 'included_in_newsletter'
    event_timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    details = Column(JSON)  # Additional event information
    source_job_id = Column(String(255))  # ID of the job that created this event
    
    # Relationships
    article = relationship("Article", back_populates="processing_events")


class Newsletter(Base):
    """Newsletter model representing compiled research summaries."""
    __tablename__ = 'newsletters'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    issue_date = Column(Date, nullable=False)
    s3_path = Column(String(512), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    articles = relationship("Article", secondary=newsletter_articles, back_populates="newsletters")
    emails = relationship("Email", back_populates="newsletter")


class Email(Base):
    """Email model for tracking sent emails."""
    __tablename__ = 'emails'
    
    id = Column(Integer, primary_key=True)
    subject = Column(String(255), nullable=False)
    newsletter_id = Column(Integer, ForeignKey('newsletters.id'))
    sent_at = Column(DateTime, default=datetime.datetime.utcnow)
    recipient_count = Column(Integer)
    s3_path = Column(String(512))
    
    # Relationships
    newsletter = relationship("Newsletter", back_populates="emails") 