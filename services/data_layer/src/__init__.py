"""
Data access layer for AtomikLabs research data system.
"""

from .db import init_db, get_session, create_tables
from .models import Article, Author, Organization, Category, ProcessingEvent, Newsletter, Email
from .repository import (
    ArticleRepository,
    AuthorRepository,
    OrganizationRepository,
    CategoryRepository,
    ProcessingEventRepository,
    NewsletterRepository,
    EmailRepository,
)
