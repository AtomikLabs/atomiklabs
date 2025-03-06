import os
import sys
import pytest
from unittest import mock

# Add the parent directory to the path so 'shared' imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Mock boto3 and other external services
@pytest.fixture(autouse=True)
def mock_boto3():
    with mock.patch("boto3.resource"), mock.patch("boto3.client"):
        yield

# Mock SQLAlchemy session
@pytest.fixture
def mock_db_session():
    session_mock = mock.MagicMock()
    with mock.patch("sqlalchemy.orm.sessionmaker", return_value=lambda: session_mock):
        yield session_mock 