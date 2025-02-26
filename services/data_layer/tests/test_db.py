"""
Unit tests for the database connection module in the data layer.
"""
import json
from unittest.mock import patch, MagicMock, call

import pytest
from botocore.exceptions import ClientError

# Import the db functions that we want to test
from src.db import (
    get_connection_string,
    get_db_secrets,
    get_session,
    init_db
)

# Import the module for patching
import src.db

class TestGetConnectionString:
    """Unit tests for get_connection_string function."""

    def test_get_connection_string_success(self):
        """Test getting connection string from secrets."""
        # Arrange
        mock_secrets = {
            "username": "test_user",
            "password": "test_pass",
            "host": "test_host",
            "port": 5432,
            "dbname": "test_db"
        }
        
        # Act
        with patch('src.db.get_db_secrets', return_value=mock_secrets):
            result = get_connection_string()
        
        # Assert
        assert result == "postgresql://test_user:test_pass@test_host:5432/test_db"

    def test_get_connection_string_from_env(self):
        """Test getting connection string from environment when secrets fail."""
        # Arrange
        mock_env_vars = {
            "DB_USERNAME": "env_user",
            "DB_PASSWORD": "env_pass",
            "DB_HOST": "env_host",
            "DB_PORT": "5433",
            "DB_NAME": "env_db"
        }
        
        def mock_getenv(name, default=None):
            return mock_env_vars.get(name, default)
        
        # Act
        with patch('src.db.get_db_secrets', side_effect=Exception("Test exception")), \
             patch('src.db.os.environ.get', side_effect=mock_getenv):
            result = get_connection_string()
        
        # Assert
        assert result == "postgresql://env_user:env_pass@env_host:5433/env_db"

    def test_get_connection_string_missing_env(self):
        """Test error when connection info is not available."""
        # Arrange
        def mock_getenv(name, default=None):
            # Return None for all environment variables
            return default
        
        # Act/Assert
        with patch('src.db.get_db_secrets', side_effect=Exception("Test exception")), \
             patch('src.db.os.environ.get', side_effect=mock_getenv):
            with pytest.raises(ValueError, match="Database connection information not available"):
                get_connection_string()


class TestGetDbSecrets:
    """Unit tests for get_db_secrets function."""

    def test_get_db_secrets_success(self):
        """Test getting secrets from Secrets Manager."""
        # Arrange
        secret_value = {
            "username": "secret_user",
            "password": "secret_pass",
            "host": "secret_host",
            "port": 5432,
            "dbname": "secret_db"
        }
        
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            'SecretString': json.dumps(secret_value)
        }
        
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client
        
        # Act
        with patch('src.db.boto3.session.Session', return_value=mock_session), \
             patch('src.db.os.environ.get', return_value="test-secret-name"):
            result = get_db_secrets()
        
        # Assert
        assert result == secret_value
        mock_session.client.assert_called_once_with(service_name='secretsmanager')
        mock_client.get_secret_value.assert_called_once_with(SecretId="test-secret-name")

    def test_get_db_secrets_missing_env(self):
        """Test error when DB_CREDENTIALS_SECRET environment variable is missing."""
        # Act/Assert
        # We need to patch boto3 completely to avoid real AWS calls
        mock_boto3 = MagicMock()
        
        with patch('src.db.boto3', mock_boto3), \
             patch('src.db.os.environ.get', return_value=None):
            with pytest.raises(ValueError, match="DB_CREDENTIALS_SECRET environment variable is required"):
                get_db_secrets()

    def test_get_db_secrets_aws_error(self):
        """Test handling AWS client errors."""
        # Arrange
        mock_client = MagicMock()
        mock_client.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Secret not found"}},
            "GetSecretValue"
        )
        
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client
        
        # Act/Assert
        with patch('src.db.boto3.session.Session', return_value=mock_session), \
             patch('src.db.os.environ.get', return_value="test-secret-name"):
            with pytest.raises(ClientError):
                get_db_secrets()


class TestInitDb:
    """Unit tests for init_db function."""

    def test_init_db_default(self):
        """Test initializing the database with default connection string."""
        # Arrange
        mock_engine = MagicMock()
        mock_sessionmaker = MagicMock()
        
        # Act
        with patch('src.db.get_connection_string', return_value="test-connection-string"), \
             patch('src.db.create_engine', return_value=mock_engine) as mock_create_engine, \
             patch('src.db.sessionmaker', return_value=mock_sessionmaker) as mock_sessionmaker_call:
            init_db()
        
        # Assert
        mock_create_engine.assert_called_once_with(
            "test-connection-string",
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )
        mock_sessionmaker_call.assert_called_once_with(
            autocommit=False, 
            autoflush=False, 
            bind=mock_engine
        )

    def test_init_db_custom_connection(self):
        """Test initializing the database with a custom connection string."""
        # Arrange
        mock_engine = MagicMock()
        mock_sessionmaker = MagicMock()
        custom_connection = "custom-connection-string"
        
        # Act
        with patch('src.db.create_engine', return_value=mock_engine) as mock_create_engine, \
             patch('src.db.sessionmaker', return_value=mock_sessionmaker) as mock_sessionmaker_call:
            init_db(custom_connection)
        
        # Assert
        mock_create_engine.assert_called_once_with(
            custom_connection,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )
        mock_sessionmaker_call.assert_called_once_with(
            autocommit=False, 
            autoflush=False, 
            bind=mock_engine
        )


class TestGetSession:
    """Unit tests for get_session function."""

    def test_get_session_initialized(self):
        """Test getting a session when DB is already initialized."""
        # Arrange
        mock_session = MagicMock()
        mock_session_class = MagicMock(return_value=mock_session)
        
        # Act
        with patch('src.db.SessionLocal', mock_session_class):
            result = get_session()
        
        # Assert
        assert result == mock_session
        mock_session_class.assert_called_once()
        mock_session.close.assert_called_once()

    def test_get_session_uninitialized(self):
        """Test getting a session when DB is not yet initialized."""
        # Arrange
        mock_session = MagicMock()
        mock_session_local = MagicMock(return_value=mock_session)
        mock_init_db = MagicMock()
        
        # Act
        with patch.object(src.db, 'SessionLocal', None, create=True), \
             patch('src.db.init_db', mock_init_db), \
             patch.object(src.db, 'sessionmaker', return_value=mock_session_local):
            
            # Set the SessionLocal to be initialized after init_db is called
            def mock_init_db_impl():
                src.db.SessionLocal = mock_session_local
            
            # Make init_db actually set the SessionLocal
            mock_init_db.side_effect = mock_init_db_impl
            
            # Call the function
            result = get_session()
        
        # Assert
        assert result == mock_session
        mock_init_db.assert_called_once()
        mock_session_local.assert_called_once()
        mock_session.close.assert_called_once() 