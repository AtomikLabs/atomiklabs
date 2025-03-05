#!/usr/bin/env python3
"""
Database connection management for the arXiv data layer.

This module handles creating and closing database connections,
using environment variables for configuration.
"""

import os
import logging
import boto3
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Global engine to be reused across Lambda invocations
_DB_ENGINE = None
_SESSION_FACTORY = None


def _get_db_password():
    """Retrieve database password from SSM Parameter Store"""
    ssm_client = boto3.client('ssm')
    password_param = os.environ.get('DB_PASSWORD_PARAM')
    
    if not password_param:
        raise ValueError("DB_PASSWORD_PARAM environment variable is not set")
    
    try:
        response = ssm_client.get_parameter(
            Name=password_param,
            WithDecryption=True
        )
        return response['Parameter']['Value']
    except Exception as e:
        logger.error(f"Failed to retrieve database password: {str(e)}")
        raise


def get_db_engine():
    """
    Create or return the SQLAlchemy engine.
    Reuses the engine across Lambda invocations for better performance.
    """
    global _DB_ENGINE
    if _DB_ENGINE is None:
        # Get database connection parameters from environment variables
        db_host = os.environ.get('DB_HOST')
        db_port = os.environ.get('DB_PORT')
        db_name = os.environ.get('DB_NAME')
        db_user = os.environ.get('DB_USER')
        
        # Validate required environment variables
        if not all([db_host, db_port, db_name, db_user]):
            missing = [var for var, val in {
                'DB_HOST': db_host,
                'DB_PORT': db_port,
                'DB_NAME': db_name,
                'DB_USER': db_user
            }.items() if not val]
            
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        # Get password from SSM Parameter Store
        db_password = _get_db_password()
        
        # Create database connection URL
        db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        # Create SQLAlchemy engine with recommended settings for Lambda
        _DB_ENGINE = create_engine(
            db_url,
            pool_pre_ping=True,  # Check connection before using
            pool_recycle=3600,   # Recycle connections after 1 hour
            pool_size=5,         # Limit pool size for Lambda concurrency
            max_overflow=10      # Allow temporary additional connections
        )
        
        logger.info(f"Created database engine for {db_host}:{db_port}/{db_name}")
    
    return _DB_ENGINE


def get_db_session_factory():
    """Get a session factory for creating new database sessions"""
    global _SESSION_FACTORY
    if _SESSION_FACTORY is None:
        engine = get_db_engine()
        _SESSION_FACTORY = scoped_session(sessionmaker(bind=engine))
        
    return _SESSION_FACTORY


def get_db_connection():
    """Get a new database session"""
    session_factory = get_db_session_factory()
    return session_factory()


def close_db_connection(session):
    """Close a database session"""
    if session:
        try:
            session.close()
        except Exception as e:
            logger.error(f"Error closing database session: {str(e)}")


@contextmanager
def db_session():
    """Context manager for database sessions"""
    session = get_db_connection()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database transaction error: {str(e)}")
        raise
    finally:
        close_db_connection(session) 