#!/usr/bin/env python3
import os
import sys
import logging

from shared.db import PostgresDB

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def create_schema(db: PostgresDB):
    """Create the database schema if it doesn't exist."""
    
    # Base tables
    db.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            id SERIAL PRIMARY KEY,
            arxiv_id TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            s3_abstract_key TEXT,
            s3_pdf_key TEXT
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS authors (
            id SERIAL PRIMARY KEY,
            surname TEXT NOT NULL,
            given_names TEXT
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS arxiv_categories (
            id SERIAL PRIMARY KEY,
            category_code TEXT UNIQUE NOT NULL,
            category_name TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS arxiv_sets (
            id SERIAL PRIMARY KEY,
            set_name TEXT UNIQUE NOT NULL
        )
    """)

    # Newsletter tracking
    db.execute("""
        CREATE TABLE IF NOT EXISTS newsletters (
            id SERIAL PRIMARY KEY,
            date TEXT NOT NULL,
            category_code TEXT NOT NULL,
            s3_key TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, category_code)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS email_batches (
            id SERIAL PRIMARY KEY,
            date TEXT NOT NULL,
            recipient_list TEXT NOT NULL,
            message_id TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS newsletter_emails (
            newsletter_id INTEGER REFERENCES newsletters(id),
            email_batch_id INTEGER REFERENCES email_batches(id),
            PRIMARY KEY (newsletter_id, email_batch_id)
        )
    """)

    # Junction tables
    db.execute("""
        CREATE TABLE IF NOT EXISTS paper_authors (
            paper_id INTEGER REFERENCES papers(id),
            author_id INTEGER REFERENCES authors(id),
            author_order INTEGER NOT NULL,
            PRIMARY KEY (paper_id, author_id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS author_organizations (
            author_id INTEGER REFERENCES authors(id),
            org_id INTEGER REFERENCES organizations(id),
            paper_id INTEGER REFERENCES papers(id),
            PRIMARY KEY (author_id, org_id, paper_id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS paper_categories (
            paper_id INTEGER REFERENCES papers(id),
            category_id INTEGER REFERENCES arxiv_categories(id),
            PRIMARY KEY (paper_id, category_id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS paper_sets (
            paper_id INTEGER REFERENCES papers(id),
            set_id INTEGER REFERENCES arxiv_sets(id),
            PRIMARY KEY (paper_id, set_id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS newsletter_papers (
            newsletter_id INTEGER REFERENCES newsletters(id),
            paper_id INTEGER REFERENCES papers(id),
            PRIMARY KEY (newsletter_id, paper_id)
        )
    """)

    # Indexes
    db.execute("CREATE INDEX IF NOT EXISTS idx_authors_surname ON authors(surname)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_paper_authors_order ON paper_authors(paper_id, author_order)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_newsletters_date ON newsletters(date)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_email_batches_date ON email_batches(date)")

def main():
    """Initialize the PostgreSQL database schema."""
    try:
        logger.info("Connecting to PostgreSQL database")
        db = PostgresDB()
        
        with db.transaction():
            logger.info("Creating database schema")
            create_schema(db)
            
        logger.info("Database initialization successful")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
