#!/usr/bin/env python3
import os
import sys
from pathlib import Path

from shared.db import SQLiteDB

def create_schema(db: SQLiteDB):
    """Create the database schema if it doesn't exist."""
    
    # Base tables
    db.execute("""
        CREATE TABLE papers (
            id INTEGER PRIMARY KEY,
            arxiv_id TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            s3_abstract_key TEXT,
            s3_pdf_key TEXT
        )
    """)

    db.execute("""
        CREATE TABLE organizations (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE authors (
            id INTEGER PRIMARY KEY,
            surname TEXT NOT NULL,
            given_names TEXT
        )
    """)

    db.execute("""
        CREATE TABLE arxiv_categories (
            id INTEGER PRIMARY KEY,
            category_code TEXT UNIQUE NOT NULL,
            category_name TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE arxiv_sets (
            id INTEGER PRIMARY KEY,
            set_name TEXT UNIQUE NOT NULL
        )
    """)

    # Newsletter tracking
    db.execute("""
        CREATE TABLE newsletters (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            category_code TEXT NOT NULL,
            s3_key TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, category_code)
        )
    """)

    db.execute("""
        CREATE TABLE email_batches (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            recipient_list TEXT NOT NULL,
            message_id TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE newsletter_emails (
            newsletter_id INTEGER,
            email_batch_id INTEGER,
            PRIMARY KEY (newsletter_id, email_batch_id),
            FOREIGN KEY (newsletter_id) REFERENCES newsletters(id),
            FOREIGN KEY (email_batch_id) REFERENCES email_batches(id)
        )
    """)

    # Junction tables
    db.execute("""
        CREATE TABLE paper_authors (
            paper_id INTEGER,
            author_id INTEGER,
            author_order INTEGER NOT NULL,
            PRIMARY KEY (paper_id, author_id),
            FOREIGN KEY (paper_id) REFERENCES papers(id),
            FOREIGN KEY (author_id) REFERENCES authors(id)
        )
    """)

    db.execute("""
        CREATE TABLE author_organizations (
            author_id INTEGER,
            org_id INTEGER,
            paper_id INTEGER,
            PRIMARY KEY (author_id, org_id, paper_id),
            FOREIGN KEY (author_id) REFERENCES authors(id),
            FOREIGN KEY (org_id) REFERENCES organizations(id),
            FOREIGN KEY (paper_id) REFERENCES papers(id)
        )
    """)

    db.execute("""
        CREATE TABLE paper_categories (
            paper_id INTEGER,
            category_id INTEGER,
            PRIMARY KEY (paper_id, category_id),
            FOREIGN KEY (paper_id) REFERENCES papers(id),
            FOREIGN KEY (category_id) REFERENCES arxiv_categories(id)
        )
    """)

    db.execute("""
        CREATE TABLE paper_sets (
            paper_id INTEGER,
            set_id INTEGER,
            PRIMARY KEY (paper_id, set_id),
            FOREIGN KEY (paper_id) REFERENCES papers(id),
            FOREIGN KEY (set_id) REFERENCES arxiv_sets(id)
        )
    """)

    db.execute("""
        CREATE TABLE newsletter_papers (
            newsletter_id INTEGER,
            paper_id INTEGER,
            PRIMARY KEY (newsletter_id, paper_id),
            FOREIGN KEY (newsletter_id) REFERENCES newsletters(id),
            FOREIGN KEY (paper_id) REFERENCES papers(id)
        )
    """)

    # Indexes
    db.execute("CREATE INDEX idx_authors_surname ON authors(surname)")
    db.execute("CREATE INDEX idx_paper_authors_order ON paper_authors(paper_id, author_order)")
    db.execute("CREATE INDEX idx_newsletters_date ON newsletters(date)")
    db.execute("CREATE INDEX idx_email_batches_date ON email_batches(date)")

def main():
    """Initialize the SQLite database if it doesn't exist."""
    db_path = os.environ.get('SQLITE_PATH', '/mnt/sqlite/arxiv.db')
    db_file = Path(db_path)

    if db_file.exists():
        print(f"Database already exists at {db_path}")
        sys.exit(0)

    db_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        print(f"Creating database at {db_path}")
        db = SQLiteDB(db_path)
        with db.transaction() as conn:
            create_schema(db)
        print("Database initialization successful")
    except Exception as e:
        print(f"Error initializing database: {e}", file=sys.stderr)
        if db_file.exists():
            db_file.unlink()
        sys.exit(1)

if __name__ == '__main__':
    main()
