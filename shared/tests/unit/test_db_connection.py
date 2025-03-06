import pytest
from unittest import mock
from shared.db.connection import (
    get_db_engine,
    get_db_connection,
    close_db_connection,
    db_session,
    _get_db_password,
    _DB_ENGINE
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

def test_get_db_engine_env_vars():
    """Test that get_db_engine validates environment variables."""
    # Mock environment variables to be missing
    with mock.patch('os.environ.get', return_value=None):
        # Ensure _DB_ENGINE is None to force a new engine creation
        with mock.patch('shared.db.connection._DB_ENGINE', None):
            # The function should raise a ValueError due to missing env vars
            with pytest.raises(ValueError) as exc_info:
                get_db_engine()
            
            # Verify the error message mentions missing variables
            assert "Missing required environment variables" in str(exc_info.value)

def test_get_db_connection():
    """Test that get_db_connection returns a session."""
    # Mock the session factory
    mock_session = mock.MagicMock(spec=Session)
    mock_session_factory = mock.MagicMock()
    mock_session_factory.return_value = mock_session
    
    with mock.patch('shared.db.connection.get_db_session_factory', return_value=mock_session_factory):
        session = get_db_connection()
        
        assert session == mock_session
        assert mock_session_factory.called

def test_db_session_context_manager():
    """Test that db_session works as a context manager."""
    mock_session = mock.MagicMock(spec=Session)
    
    with mock.patch('shared.db.connection.get_db_connection', return_value=mock_session):
        with db_session() as session:
            assert session == mock_session
        
        # Verify that commit and close were called
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

def test_db_session_context_manager_exception():
    """Test that db_session handles exceptions correctly."""
    mock_session = mock.MagicMock(spec=Session)
    test_exception = ValueError("Test exception")
    
    with mock.patch('shared.db.connection.get_db_connection', return_value=mock_session):
        with pytest.raises(ValueError):
            with db_session() as session:
                assert session == mock_session
                raise test_exception
        
        # Verify that rollback and close were called
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()
        
def test_close_db_connection():
    """Test that close_db_connection closes the session."""
    mock_session = mock.MagicMock(spec=Session)
    
    close_db_connection(mock_session)
    
    mock_session.close.assert_called_once()

def test_close_db_connection_exception():
    """Test that close_db_connection handles exceptions gracefully."""
    mock_session = mock.MagicMock(spec=Session)
    mock_session.close.side_effect = Exception("Test exception")
    
    # This should not raise an exception
    close_db_connection(mock_session)
    
    mock_session.close.assert_called_once()

def test_get_db_password():
    """Test that _get_db_password retrieves the password from SSM."""
    # Mock environment variables
    env_vars = {
        'DB_PASSWORD_PARAM': '/dev/db/password'
    }
    
    mock_ssm_client = mock.MagicMock()
    mock_ssm_client.get_parameter.return_value = {
        'Parameter': {
            'Value': 'testpassword'
        }
    }
    
    with mock.patch('os.environ.get', side_effect=lambda key, default=None: env_vars.get(key, default)):
        with mock.patch('boto3.client', return_value=mock_ssm_client):
            password = _get_db_password()
            
            assert password == 'testpassword'
            mock_ssm_client.get_parameter.assert_called_once_with(
                Name='/dev/db/password',
                WithDecryption=True
            ) 