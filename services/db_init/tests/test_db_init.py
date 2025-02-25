import os
import pytest

from shared.db import PostgresDB
from src.db_init import main

def test_schema_creation(schema_db):
    """Test that all tables and indexes are created correctly."""
    with schema_db.transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        tables = cursor.fetchall()
        table_names = {t[0] for t in tables}
    
    expected_tables = {
        'papers',
        'organizations',
        'authors',
        'arxiv_categories',
        'arxiv_sets',
        'newsletters',
        'email_batches',
        'newsletter_emails',
        'paper_authors',
        'author_organizations',
        'paper_categories',
        'paper_sets',
        'newsletter_papers'
    }
    
    assert table_names == expected_tables

    with schema_db.transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT indexname FROM pg_indexes
            WHERE schemaname = 'public'
        """)
        indexes = cursor.fetchall()
        index_names = {i[0] for i in indexes}
    
    expected_indexes = {
        'idx_authors_surname',
        'idx_paper_authors_order',
        'idx_newsletters_date',
        'idx_email_batches_date'
    }
    
    assert expected_indexes.issubset(index_names)

def test_table_schemas(schema_db):
    """Test that table schemas match expected structure."""
    with schema_db.transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'papers' AND table_schema = 'public'
        """)
        papers_info = cursor.fetchall()
    
    column_info = {col[0]: (col[1], col[2]) for col in papers_info}
    assert 'id' in column_info
    assert column_info['id'][0] == 'integer'  # type
    assert 'arxiv_id' in column_info
    assert column_info['arxiv_id'][0] == 'text'
    assert column_info['arxiv_id'][1] == 'NO'  # not null

    with schema_db.transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'authors' AND table_schema = 'public'
        """)
        author_columns = [row[0] for row in cursor.fetchall()]
    
    assert 'id' in author_columns
    assert 'surname' in author_columns
    assert 'given_names' in author_columns

def test_foreign_keys(schema_db):
    """Test that foreign key constraints are properly set up."""
    with schema_db.transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                tc.table_name, kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = 'paper_authors'
        """)
        fks = cursor.fetchall()
    
    fk_refs = {(fk[2], fk[1], fk[3]) for fk in fks}  # (ref_table, from_col, to_col)
    assert ('papers', 'paper_id', 'id') in fk_refs
    assert ('authors', 'author_id', 'id') in fk_refs

def test_idempotency(clean_db):
    """Test that running the script multiple times is safe."""
    # Set environment variables for main function
    os.environ['DB_HOST'] = clean_db.connection_params['host']
    os.environ['DB_PORT'] = clean_db.connection_params['port']
    os.environ['DB_USER'] = clean_db.connection_params['user']
    os.environ['DB_PASSWORD'] = clean_db.connection_params['password']
    os.environ['DB_NAME'] = clean_db.connection_params['dbname']
    
    # Run the main function once
    main()
    
    # Verify tables exist
    with clean_db.transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
        count1 = cursor.fetchone()[0]
    
    # Run main again to check idempotency
    main()
    
    # Verify tables still exist with same count
    with clean_db.transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
        count2 = cursor.fetchone()[0]
    
    assert count1 == count2
