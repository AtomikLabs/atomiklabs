import os
import sqlite3
from unittest.mock import patch
import pytest
from init_db import init_db

def test_db_creation(tmp_path):
    """Test database is created with correct schema when it doesn't exist."""
    # Setup
    db_dir = tmp_path / "db"
    db_path = db_dir / "app.db"
    
    with patch('init_db.DB_DIR', str(db_dir)), \
         patch('init_db.DB_PATH', str(db_path)):
        # Execute
        init_db()
        
        # Verify
        assert db_path.exists()
        
        # Check schema
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        expected_tables = {
            'papers', 'authors', 'categories', 'paper_authors',
            'paper_categories', 'citations', 'paper_metrics',
            'paper_topics', 'sqlite_sequence'  # Include SQLite's internal table
        }
        assert tables == expected_tables
        
        # Verify categories were populated
        cursor.execute("SELECT COUNT(*) FROM categories")
        category_count = cursor.fetchone()[0]
        assert category_count == 40  # Number of CS categories
        
        # Check specific category
        cursor.execute("SELECT name FROM categories WHERE code = 'AI'")
        ai_category = cursor.fetchone()[0]
        assert ai_category == "Computer Science - Artificial Intelligence"
        
        # Verify indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}
        expected_indexes = {
            'idx_papers_date',
            'idx_papers_primary_category',
            'idx_paper_authors_author',
            'idx_paper_categories_category',
            'idx_citations_cited',
            'idx_paper_metrics_scores',
            'idx_paper_topics_topic'
        }
        assert expected_indexes.issubset(indexes)
        
        conn.close()

def test_db_already_exists(tmp_path):
    """Test handling of existing database."""
    # Setup
    db_dir = tmp_path / "db"
    db_path = db_dir / "app.db"
    db_dir.mkdir()
    
    # Create a dummy database
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE dummy (id INTEGER PRIMARY KEY)")
    conn.close()
    
    # Mock logger to capture log messages
    with patch('init_db.DB_DIR', str(db_dir)), \
         patch('init_db.DB_PATH', str(db_path)), \
         patch('init_db.logger') as mock_logger:
        
        # Execute
        init_db()
        
        # Verify
        mock_logger.info.assert_any_call(f"Database already exists at {db_path}")
        mock_logger.info.assert_any_call("Successfully verified database connection")
        
        # Verify original table still exists
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert 'dummy' in tables
        conn.close()

def test_db_directory_creation(tmp_path):
    """Test database directory is created if it doesn't exist."""
    # Setup
    db_dir = tmp_path / "nonexistent" / "db"
    db_path = db_dir / "app.db"
    
    with patch('init_db.DB_DIR', str(db_dir)), \
         patch('init_db.DB_PATH', str(db_path)):
        # Execute
        init_db()
        
        # Verify
        assert db_dir.exists()
        assert db_path.exists()

def test_db_permissions_error(tmp_path):
    """Test handling of permission errors."""
    # Setup
    db_dir = tmp_path / "db"
    db_path = db_dir / "app.db"
    db_dir.mkdir()
    
    def raise_permission_error(*args, **kwargs):
        raise PermissionError("Permission denied")
    
    with patch('init_db.DB_DIR', str(db_dir)), \
         patch('init_db.DB_PATH', str(db_path)), \
         patch('sqlite3.connect', side_effect=raise_permission_error), \
         patch('init_db.logger') as mock_logger, \
         pytest.raises(PermissionError):
        
        # Execute
        init_db()
        
        # Verify
        mock_logger.error.assert_called_with("Failed to initialize database: Permission denied")

def test_foreign_keys_enabled(tmp_path):
    """Test that foreign key constraints are enabled."""
    # Setup
    db_dir = tmp_path / "db"
    db_path = db_dir / "app.db"
    
    with patch('init_db.DB_DIR', str(db_dir)), \
         patch('init_db.DB_PATH', str(db_path)):
        # Execute
        init_db()
        
        # Verify
        conn = sqlite3.connect(str(db_path))
        
        # Enable foreign keys for this connection
        conn.execute("PRAGMA foreign_keys = ON")
        
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys")
        foreign_keys_enabled = cursor.fetchone()[0]
        assert foreign_keys_enabled == 1
        
        # Test foreign key constraint
        cursor.execute("""
            INSERT INTO papers (
                id, title, abstract, date, abstract_url, pdf_url, 
                primary_category, processed_date
            ) VALUES (
                'test1', 'Test Title', 'Abstract', '2024-02-21',
                'http://test.com', 'http://test.com/pdf', 'AI',
                datetime('now')
            )
        """)
        
        with pytest.raises(sqlite3.IntegrityError):
            # This should fail because paper_id doesn't exist
            cursor.execute(
                "INSERT INTO paper_metrics (paper_id, citation_count) VALUES (?, ?)",
                ('nonexistent', 0)
            )
        
        conn.close()

def test_schema_constraints(tmp_path):
    """Test schema constraints are properly enforced."""
    # Setup
    db_dir = tmp_path / "db"
    db_path = db_dir / "app.db"
    
    with patch('init_db.DB_DIR', str(db_dir)), \
         patch('init_db.DB_PATH', str(db_path)):
        # Execute
        init_db()
        
        # Verify
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Test NOT NULL constraints
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("INSERT INTO papers (id) VALUES (?)", ('test1',))
        
        # Test UNIQUE constraints
        cursor.execute("INSERT INTO authors (first_name, last_name) VALUES (?, ?)", ('John', 'Doe'))
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("INSERT INTO authors (first_name, last_name) VALUES (?, ?)", ('John', 'Doe'))
        
        # Test PRIMARY KEY constraints
        cursor.execute("INSERT INTO categories (code, name) VALUES (?, ?)", ('TEST', 'Test Category'))
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("INSERT INTO categories (code, name) VALUES (?, ?)", ('TEST', 'Another Test'))
        
        conn.close()

def test_category_data_integrity(tmp_path):
    """Test that all expected categories are properly inserted."""
    # Setup
    db_dir = tmp_path / "db"
    db_path = db_dir / "app.db"
    
    with patch('init_db.DB_DIR', str(db_dir)), \
         patch('init_db.DB_PATH', str(db_path)):
        # Execute
        init_db()
        
        # Verify
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check all expected categories
        expected_categories = {
            'AI': 'Computer Science - Artificial Intelligence',
            'CL': 'Computer Science - Computation and Language',
            'CR': 'Computer Science - Cryptography and Security',
            'CV': 'Computer Science - Computer Vision and Pattern Recognition',
            'RO': 'Computer Science - Robotics'
        }
        
        for code, name in expected_categories.items():
            cursor.execute("SELECT name FROM categories WHERE code = ?", (code,))
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == name
        
        conn.close() 