import os
import logging
from contextlib import contextmanager
from typing import Any, ContextManager, List, Dict, Tuple, Optional, Union

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

logger = logging.getLogger(__name__)

class DatabaseInterface:
    """Interface for database operations."""
    def execute(self, query: str, params: Any = None) -> Any:
        """Execute raw SQL query with optional parameters."""
        raise NotImplementedError

    def transaction(self) -> ContextManager:
        """Context manager for transaction handling."""
        raise NotImplementedError

class PostgresDB(DatabaseInterface):
    """PostgreSQL implementation of database interface."""
    _pool = None
    
    def __init__(self, connection_params: Optional[Dict[str, str]] = None):
        """Initialize PostgreSQL database connection.
        
        Args:
            connection_params: Connection parameters. If None, read from environment.
        """
        if connection_params is None:
            # Read from SSM parameters stored as environment variables
            self.connection_params = {
                'dbname': os.environ.get('DB_NAME', 'arxiv'),
                'user': os.environ.get('DB_USER', 'arxiv_app'),
                'password': os.environ.get('DB_PASSWORD', ''),
                'host': os.environ.get('DB_HOST', 'localhost'),
                'port': os.environ.get('DB_PORT', '5432')
            }
        else:
            self.connection_params = connection_params
        
        # Initialize connection pool if not already initialized
        if PostgresDB._pool is None:
            self._setup_connection_pool()
    
    def _setup_connection_pool(self, min_connections: int = 1, max_connections: int = 10):
        """Set up connection pool for better performance."""
        try:
            PostgresDB._pool = ThreadedConnectionPool(
                min_connections,
                max_connections,
                **self.connection_params
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Error initializing connection pool: {e}")
            raise
    
    def execute(self, query: str, params: Any = None) -> Any:
        """Execute a SQL query.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Query result cursor
        """
        if PostgresDB._pool is None:
            self._setup_connection_pool()
            
        conn = PostgresDB._pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                # For SELECT queries, the cursor becomes iterable
                if cursor.description:
                    return cursor
                # For other queries, just return affected rows
                return cursor.rowcount
        except Exception as e:
            conn.rollback()
            logger.error(f"Database query error: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise
        finally:
            PostgresDB._pool.putconn(conn)
    
    @contextmanager
    def transaction(self):
        """Provide transaction context.
        
        Yields:
            Database connection within a transaction
        """
        if PostgresDB._pool is None:
            self._setup_connection_pool()
            
        conn = PostgresDB._pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction error: {e}")
            raise
        finally:
            PostgresDB._pool.putconn(conn)
            
    def query_one(self, query: str, params: Any = None) -> Optional[Dict]:
        """Execute query and return single row as dictionary.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Single row as dictionary or None if no rows
        """
        if PostgresDB._pool is None:
            self._setup_connection_pool()
            
        conn = PostgresDB._pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params or ())
                result = cursor.fetchone()
                return dict(result) if result else None
        finally:
            PostgresDB._pool.putconn(conn)
            
    def query_all(self, query: str, params: Any = None) -> List[Dict]:
        """Execute query and return all rows as dictionaries.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            List of rows as dictionaries
        """
        if PostgresDB._pool is None:
            self._setup_connection_pool()
            
        conn = PostgresDB._pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params or ())
                results = cursor.fetchall()
                return [dict(row) for row in results]
        finally:
            PostgresDB._pool.putconn(conn) 