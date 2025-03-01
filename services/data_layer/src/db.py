"""
Database connection module for accessing the PostgreSQL database.
"""

import json
import logging
import os
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

logger = logging.getLogger(__name__)


def get_db_secrets() -> dict:
    """
    Get database credentials from AWS Secrets Manager.

    Returns:
        dict: A dictionary containing database credentials
    """
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager")

    # Get the secret name from environment variables
    secret_name = os.environ.get("DB_CREDENTIALS_SECRET")
    if not secret_name:
        raise ValueError("DB_CREDENTIALS_SECRET environment variable is required")

    try:
        response = client.get_secret_value(SecretId=secret_name)
        if "SecretString" in response:
            return json.loads(response["SecretString"])
        else:
            raise ValueError("Secret value is not a string")
    except ClientError as e:
        logger.error(f"Error retrieving database credentials: {e}")
        raise


def get_connection_string() -> str:
    """
    Build a connection string for SQLAlchemy.

    Returns:
        str: SQLAlchemy connection string
    """
    # Try to get credentials from AWS Secrets Manager
    try:
        credentials = get_db_secrets()
        username = credentials["username"]
        password = credentials["password"]
        host = credentials["host"]
        port = credentials.get("port", 5432)
        dbname = credentials["dbname"]

        return f"postgresql://{username}:{password}@{host}:{port}/{dbname}"
    except Exception as e:
        logger.error(f"Error creating connection string from secrets: {e}")

        # Fall back to environment variables for local development
        username = os.environ.get("DB_USERNAME")
        password = os.environ.get("DB_PASSWORD")
        host = os.environ.get("DB_HOST")
        port = os.environ.get("DB_PORT", "5432")
        dbname = os.environ.get("DB_NAME")

        if not all([username, password, host, dbname]):
            logger.error("Database connection information not available")
            raise ValueError("Database connection information not available")

        return f"postgresql://{username}:{password}@{host}:{port}/{dbname}"


# Create a global engine
engine = None
SessionLocal = None


def init_db(connection_string: Optional[str] = None) -> None:
    """
    Initialize the database engine and session factory.

    Args:
        connection_string: Optional connection string override
    """
    global engine, SessionLocal

    if connection_string is None:
        connection_string = get_connection_string()

    # Create engine with connection pooling
    engine = create_engine(
        connection_string,
        pool_pre_ping=True,  # Verify connections before using them
        pool_recycle=3600,  # Recycle connections after 1 hour
        echo=False,  # Set to True for SQL debug logging
    )

    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session() -> Session:
    """
    Get a database session.

    Returns:
        Session: SQLAlchemy database session

    Note:
        This should typically be used as a context manager:
        ```
        with get_session() as session:
            # Do database operations
        ```
    """
    global SessionLocal

    # Initialize the database if it hasn't been initialized yet
    if SessionLocal is None:
        init_db()

    session = SessionLocal()
    try:
        return session
    finally:
        session.close()


def create_tables() -> None:
    """Create all tables defined in the models."""
    global engine

    if engine is None:
        init_db()

    Base.metadata.create_all(bind=engine)
