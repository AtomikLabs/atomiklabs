import os
from pathlib import Path

import pytest

from shared.db import SQLiteDB
from src.db_init import main

def test_schema_creation(schema_db):
    """Test that all tables and indexes are created correctly."""
    tables = schema_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = {t[0] for t in tables}
    
    expected_tables = {
        'papers',
        'organizations',
        'authors',
        'arxiv_categories',
        'arxiv_sets',
        'paper_authors',
        'author_organizations',
        'paper_categories',
        'paper_sets'
    }
    
    assert table_names == expected_tables

    indexes = schema_db.execute(
        "SELECT name FROM sqlite_master WHERE type='index'"
    ).fetchall()
    index_names = {i[0] for i in indexes}
    
    expected_indexes = {
        'idx_authors_surname',
        'idx_paper_authors_order'
    }
    
    assert expected_indexes.issubset(index_names)

def test_table_schemas(schema_db):
    """Test that table schemas match expected structure."""
    papers_info = schema_db.execute("PRAGMA table_info(papers)").fetchall()
    assert len(papers_info) == 3
    assert papers_info[0][1] == 'id'  # name
    assert papers_info[0][2] == 'INTEGER'  # type
    assert papers_info[1][1] == 'arxiv_id'
    assert papers_info[1][2] == 'TEXT'
    assert papers_info[1][3] == 0  # notnull
    assert papers_info[1][5] == 0  # pk

    authors_info = schema_db.execute("PRAGMA table_info(authors)").fetchall()
    assert len(authors_info) == 3
    assert authors_info[0][1] == 'id'
    assert authors_info[1][1] == 'surname'
    assert authors_info[2][1] == 'given_names'

def test_foreign_keys(schema_db):
    """Test that foreign key constraints are properly set up."""
    fks = schema_db.execute("PRAGMA foreign_key_list(paper_authors)").fetchall()
    fk_refs = {(fk[2], fk[3], fk[4]) for fk in fks}  # (table, from, to)
    assert ('papers', 'paper_id', 'id') in fk_refs
    assert ('authors', 'author_id', 'id') in fk_refs

def test_idempotency(temp_db):
    """Test that running the script multiple times is safe."""
    main()
    assert Path(temp_db).exists()

    main()
    assert Path(temp_db).exists()
