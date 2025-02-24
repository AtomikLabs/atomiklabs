import os
import tempfile
from pathlib import Path

import pytest

from shared.db import SQLiteDB
from src.db_init import create_schema

@pytest.fixture
def temp_db():
    """Create a temporary SQLite database file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        os.environ["SQLITE_PATH"] = str(db_path)
        yield db_path

@pytest.fixture
def schema_db(temp_db):
    """Create a database with schema."""
    db = SQLiteDB(temp_db)
    with db.transaction() as conn:
        create_schema(db)
    return db
