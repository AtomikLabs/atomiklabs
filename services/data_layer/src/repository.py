"""
Repository module providing data access layer for database operations.
"""

import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .models import (
    Article, Author, Organization, Category, 
    ProcessingEvent, Newsletter, Email
)

logger = logging.getLogger(__name__)


class ArticleRepository:
    """Repository for Article-related database operations."""
    
    @staticmethod
    def create_article(
        session: Session,
        source_id: str,
        source: str,
        title: str,
        publication_date: date,
        abstract_text: Optional[str] = None,
        s3_abstract_path: Optional[str] = None,
        s3_fulltext_path: Optional[str] = None,
        url: Optional[str] = None
    ) -> Article:
        """
        Create a new article.
        
        Args:
            session: Database session
            source_id: External ID from source system (e.g., arXiv ID)
            source: Source system (e.g., "arxiv")
            title: Article title
            publication_date: Publication date
            abstract_text: Article abstract text
            s3_abstract_path: S3 path to abstract file
            s3_fulltext_path: S3 path to full text file
            url: URL to original article
            
        Returns:
            Article: Created article
        """
        article = Article(
            source_id=source_id,
            source=source,
            title=title,
            publication_date=publication_date,
            abstract_text=abstract_text,
            s3_abstract_path=s3_abstract_path,
            s3_fulltext_path=s3_fulltext_path,
            url=url
        )
        
        try:
            session.add(article)
            session.commit()
            return article
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating article: {e}")
            raise
    
    @staticmethod
    def get_article(session: Session, article_id: int) -> Optional[Article]:
        """
        Get an article by ID.
        
        Args:
            session: Database session
            article_id: Article ID
            
        Returns:
            Article or None: Found article or None if not found
        """
        return session.query(Article).filter(Article.id == article_id).first()
    
    @staticmethod
    def get_article_by_source_id(
        session: Session, source: str, source_id: str
    ) -> Optional[Article]:
        """
        Get an article by source and source_id.
        
        Args:
            session: Database session
            source: Source system (e.g., "arxiv")
            source_id: External ID from source system (e.g., arXiv ID)
            
        Returns:
            Article or None: Found article or None if not found
        """
        return session.query(Article).filter(
            Article.source == source,
            Article.source_id == source_id
        ).first()
    
    @staticmethod
    def add_author_to_article(
        session: Session, article_id: int, author_id: int, order: int
    ) -> None:
        """
        Add an author to an article with ordering.
        
        Args:
            session: Database session
            article_id: Article ID
            author_id: Author ID
            order: Order of the author in the author list
        """
        article = ArticleRepository.get_article(session, article_id)
        author = AuthorRepository.get_author(session, author_id)
        
        if not article or not author:
            raise ValueError("Article or author not found")
        
        # Check if association already exists
        stmt = session.query(article.authors.through).filter_by(
            article_id=article_id, author_id=author_id
        )
        
        if not session.query(stmt.exists()).scalar():
            # Add association with order
            session.execute(
                article.authors.through.insert().values(
                    article_id=article_id, author_id=author_id, author_order=order
                )
            )
            session.commit()
    
    @staticmethod
    def add_category_to_article(
        session: Session, article_id: int, category_id: int, is_primary: bool = False
    ) -> None:
        """
        Add a category to an article.
        
        Args:
            session: Database session
            article_id: Article ID
            category_id: Category ID
            is_primary: Whether this is the primary category
        """
        article = ArticleRepository.get_article(session, article_id)
        category = CategoryRepository.get_category(session, category_id)
        
        if not article or not category:
            raise ValueError("Article or category not found")
        
        # Check if association already exists
        stmt = session.query(article.categories.through).filter_by(
            article_id=article_id, category_id=category_id
        )
        
        if not session.query(stmt.exists()).scalar():
            # Add association
            session.execute(
                article.categories.through.insert().values(
                    article_id=article_id, category_id=category_id, is_primary=is_primary
                )
            )
            session.commit()
        elif is_primary:
            # Update existing association to set as primary
            session.execute(
                article.categories.through.update().where(
                    article.categories.through.c.article_id == article_id,
                    article.categories.through.c.category_id == category_id
                ).values(is_primary=True)
            )
            session.commit()


class AuthorRepository:
    """Repository for Author-related database operations."""
    
    @staticmethod
    def create_author(
        session: Session, name: str, email: Optional[str] = None
    ) -> Author:
        """
        Create a new author or get existing one by name.
        
        Args:
            session: Database session
            name: Author name
            email: Author email
            
        Returns:
            Author: Created or retrieved author
        """
        # Check if author already exists
        author = session.query(Author).filter(Author.name == name).first()
        
        if author:
            # Update email if provided and different
            if email and author.email != email:
                author.email = email
                session.commit()
            return author
        
        author = Author(name=name, email=email)
        
        try:
            session.add(author)
            session.commit()
            return author
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating author: {e}")
            raise
    
    @staticmethod
    def get_author(session: Session, author_id: int) -> Optional[Author]:
        """
        Get an author by ID.
        
        Args:
            session: Database session
            author_id: Author ID
            
        Returns:
            Author or None: Found author or None if not found
        """
        return session.query(Author).filter(Author.id == author_id).first()
    
    @staticmethod
    def add_organization_to_author(
        session: Session, author_id: int, organization_id: int
    ) -> None:
        """
        Associate an author with an organization.
        
        Args:
            session: Database session
            author_id: Author ID
            organization_id: Organization ID
        """
        author = AuthorRepository.get_author(session, author_id)
        organization = OrganizationRepository.get_organization(
            session, organization_id
        )
        
        if not author or not organization:
            raise ValueError("Author or organization not found")
        
        author.organizations.append(organization)
        session.commit()


class OrganizationRepository:
    """Repository for Organization-related database operations."""
    
    @staticmethod
    def create_organization(
        session: Session, name: str, country: Optional[str] = None
    ) -> Organization:
        """
        Create a new organization or get existing one by name.
        
        Args:
            session: Database session
            name: Organization name
            country: Organization country
            
        Returns:
            Organization: Created or retrieved organization
        """
        # Check if organization already exists
        org = session.query(Organization).filter(Organization.name == name).first()
        
        if org:
            # Update country if provided and different
            if country and org.country != country:
                org.country = country
                session.commit()
            return org
        
        org = Organization(name=name, country=country)
        
        try:
            session.add(org)
            session.commit()
            return org
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating organization: {e}")
            raise
    
    @staticmethod
    def get_organization(
        session: Session, organization_id: int
    ) -> Optional[Organization]:
        """
        Get an organization by ID.
        
        Args:
            session: Database session
            organization_id: Organization ID
            
        Returns:
            Organization or None: Found organization or None if not found
        """
        return session.query(Organization).filter(
            Organization.id == organization_id
        ).first()


class CategoryRepository:
    """Repository for Category-related database operations."""
    
    @staticmethod
    def create_category(
        session: Session, name: str, code: str, parent_id: Optional[int] = None
    ) -> Category:
        """
        Create a new category or get existing one by code.
        
        Args:
            session: Database session
            name: Category name
            code: Category code
            parent_id: Parent category ID
            
        Returns:
            Category: Created or retrieved category
        """
        # Check if category already exists
        category = session.query(Category).filter(Category.code == code).first()
        
        if category:
            # Update name if different
            if category.name != name:
                category.name = name
                session.commit()
            return category
        
        category = Category(name=name, code=code, parent_id=parent_id)
        
        try:
            session.add(category)
            session.commit()
            return category
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating category: {e}")
            raise
    
    @staticmethod
    def get_category(session: Session, category_id: int) -> Optional[Category]:
        """
        Get a category by ID.
        
        Args:
            session: Database session
            category_id: Category ID
            
        Returns:
            Category or None: Found category or None if not found
        """
        return session.query(Category).filter(Category.id == category_id).first()
    
    @staticmethod
    def get_category_by_code(session: Session, code: str) -> Optional[Category]:
        """
        Get a category by code.
        
        Args:
            session: Database session
            code: Category code
            
        Returns:
            Category or None: Found category or None if not found
        """
        return session.query(Category).filter(Category.code == code).first()


class ProcessingEventRepository:
    """Repository for ProcessingEvent-related database operations."""
    
    @staticmethod
    def create_event(
        session: Session,
        article_id: int,
        event_type: str,
        details: Optional[Dict[str, Any]] = None,
        source_job_id: Optional[str] = None
    ) -> ProcessingEvent:
        """
        Create a new processing event.
        
        Args:
            session: Database session
            article_id: Article ID
            event_type: Event type
            details: Event details
            source_job_id: Source job ID
            
        Returns:
            ProcessingEvent: Created processing event
        """
        event = ProcessingEvent(
            article_id=article_id,
            event_type=event_type,
            details=details,
            source_job_id=source_job_id
        )
        
        try:
            session.add(event)
            session.commit()
            return event
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating processing event: {e}")
            raise


class NewsletterRepository:
    """Repository for Newsletter-related database operations."""
    
    @staticmethod
    def create_newsletter(
        session: Session, title: str, issue_date: date, s3_path: str
    ) -> Newsletter:
        """
        Create a new newsletter.
        
        Args:
            session: Database session
            title: Newsletter title
            issue_date: Issue date
            s3_path: S3 path to newsletter file
            
        Returns:
            Newsletter: Created newsletter
        """
        newsletter = Newsletter(
            title=title,
            issue_date=issue_date,
            s3_path=s3_path
        )
        
        try:
            session.add(newsletter)
            session.commit()
            return newsletter
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating newsletter: {e}")
            raise
    
    @staticmethod
    def add_article_to_newsletter(
        session: Session,
        newsletter_id: int,
        article_id: int,
        section: Optional[str] = None,
        priority: Optional[int] = None
    ) -> None:
        """
        Add an article to a newsletter.
        
        Args:
            session: Database session
            newsletter_id: Newsletter ID
            article_id: Article ID
            section: Section name
            priority: Priority within section
        """
        newsletter = session.query(Newsletter).filter(
            Newsletter.id == newsletter_id
        ).first()
        
        article = session.query(Article).filter(Article.id == article_id).first()
        
        if not newsletter or not article:
            raise ValueError("Newsletter or article not found")
        
        # Check if association already exists
        stmt = session.query(newsletter.articles.through).filter_by(
            newsletter_id=newsletter_id, article_id=article_id
        )
        
        if not session.query(stmt.exists()).scalar():
            # Add association with section and priority
            session.execute(
                newsletter.articles.through.insert().values(
                    newsletter_id=newsletter_id,
                    article_id=article_id,
                    section=section,
                    priority=priority
                )
            )
            session.commit()
    
    @staticmethod
    def get_newsletter(session: Session, newsletter_id: int) -> Optional[Newsletter]:
        """
        Get a newsletter by ID.
        
        Args:
            session: Database session
            newsletter_id: Newsletter ID
            
        Returns:
            Newsletter or None: Found newsletter or None if not found
        """
        return session.query(Newsletter).filter(
            Newsletter.id == newsletter_id
        ).first()
    
    @staticmethod
    def get_newsletter_by_date(
        session: Session, issue_date: date
    ) -> Optional[Newsletter]:
        """
        Get a newsletter by issue date.
        
        Args:
            session: Database session
            issue_date: Issue date
            
        Returns:
            Newsletter or None: Found newsletter or None if not found
        """
        return session.query(Newsletter).filter(
            Newsletter.issue_date == issue_date
        ).first()


class EmailRepository:
    """Repository for Email-related database operations."""
    
    @staticmethod
    def create_email(
        session: Session,
        subject: str,
        newsletter_id: int,
        recipient_count: int,
        s3_path: Optional[str] = None
    ) -> Email:
        """
        Create a new email record.
        
        Args:
            session: Database session
            subject: Email subject
            newsletter_id: Associated newsletter ID
            recipient_count: Number of recipients
            s3_path: S3 path to email content
            
        Returns:
            Email: Created email record
        """
        email = Email(
            subject=subject,
            newsletter_id=newsletter_id,
            recipient_count=recipient_count,
            s3_path=s3_path
        )
        
        try:
            session.add(email)
            session.commit()
            return email
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating email record: {e}")
            raise 