import sqlite3
from contextlib import contextmanager
from typing import Any, ContextManager

class DatabaseInterface:
    """Interface for database operations."""
    def execute(self, query: str, params: tuple = None) -> Any:
        """Execute raw SQL query with optional parameters."""
        raise NotImplementedError

    def transaction(self) -> ContextManager:
        """Context manager for transaction handling."""
        raise NotImplementedError

class SQLiteDB(DatabaseInterface):
    """SQLite implementation of database interface."""
    def __init__(self, db_path: str):
        self.db_path = db_path

    def execute(self, query: str, params: tuple = None) -> Any:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            return conn.execute(query, params or ())

    @contextmanager
    def transaction(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
