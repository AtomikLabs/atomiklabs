import os
import tempfile
import pytest
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from shared.db import PostgresDB
from src.db_init import create_schema

# Use environment variables or defaults for test database connection
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_USER = os.environ.get('DB_USER', 'arxiv_test')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'test_password')
DB_NAME = os.environ.get('DB_NAME', 'arxiv_test')

@pytest.fixture(scope="session")
def pg_connection_params():
    """Return PostgreSQL connection parameters for tests."""
    return {
        'host': DB_HOST,
        'port': DB_PORT,
        'user': DB_USER,
        'password': DB_PASSWORD,
        'dbname': DB_NAME
    }

@pytest.fixture(scope="function")
def clean_db(pg_connection_params):
    """Create a clean database for each test."""
    # Connect to PostgreSQL
    conn = psycopg2.connect(
        host=pg_connection_params['host'],
        port=pg_connection_params['port'],
        user=pg_connection_params['user'],
        password=pg_connection_params['password'],
        dbname=pg_connection_params['dbname']
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    # Clean up any existing tables
    with conn.cursor() as cursor:
        cursor.execute("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
            END $$;
        """)
    
    conn.close()
    
    # Return a PostgresDB instance
    return PostgresDB(pg_connection_params)

@pytest.fixture
def schema_db(clean_db):
    """Create a database with schema."""
    with clean_db.transaction():
        create_schema(clean_db)
    return clean_db
