"""Neo4j client package for interacting with Neo4j graph databases."""

__version__ = "0.1.0"

from .client import Neo4jClient
from .models import (
    Paper, 
    Author, 
    Category, 
    Set,
    Relationship,
    AuthoredBy,
    CategorizedAs,
    BelongsTo
)
from .exceptions import (
    Neo4jError,
    Neo4jConnectionError,
    Neo4jAuthError,
    Neo4jQueryError,
    Neo4jTransactionError,
    Neo4jNodeNotFoundError
)
from .schema import setup_schema, verify_schema

__all__ = [
    "Neo4jClient",
    "Paper",
    "Author",
    "Category",
    "Set",
    "Relationship",
    "AuthoredBy",
    "CategorizedAs",
    "BelongsTo",
    "Neo4jError",
    "Neo4jConnectionError",
    "Neo4jAuthError",
    "Neo4jQueryError",
    "Neo4jTransactionError",
    "Neo4jNodeNotFoundError",
    "setup_schema",
    "verify_schema"
]

def hello_world():
    return "Hello from Neo4j client"
