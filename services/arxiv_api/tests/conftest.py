"""
Common fixtures for tests
"""
import json
import os
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

# Mock os.environ.get to return test values for environment variables
original_os_environ_get = os.environ.get
def mock_os_environ_get(key, default=None):
    mock_env = {
        'CONFIG_PATH': '/test/config',
        'ENVIRONMENT': 'test',
        'REGION': 'us-test-1',
        'S3_BUCKET': 'test-bucket'
    }
    return mock_env.get(key, default)

os.environ.get = mock_os_environ_get

# Replace boto3, botocore, and sqlalchemy with mocks right at import time
# This must be done before any other imports that might use these modules
sys.modules['sqlalchemy'] = MagicMock()
sys.modules['sqlalchemy.orm'] = MagicMock()
sys.modules['sqlalchemy.exc'] = MagicMock()
sys.modules['sqlalchemy.dialects'] = MagicMock()
sys.modules['sqlalchemy.dialects.postgresql'] = MagicMock()
sys.modules['sqlalchemy.ext'] = MagicMock()
sys.modules['sqlalchemy.ext.declarative'] = MagicMock()
sys.modules['boto3'] = MagicMock()
sys.modules['botocore'] = MagicMock()
sys.modules['botocore.stub'] = MagicMock()
sys.modules['botocore.exceptions'] = MagicMock()

# Mock shared modules
sys.modules['shared'] = MagicMock()
sys.modules['shared.db'] = MagicMock()
sys.modules['shared.models'] = MagicMock()
sys.modules['shared.models.schemas'] = MagicMock()

# Setup ClientError mock
class MockClientError(Exception):
    pass

sys.modules['botocore.exceptions'].ClientError = MockClientError

# Setup SQLAlchemyError mock
class MockSQLAlchemyError(Exception):
    pass

sys.modules['sqlalchemy.exc'].SQLAlchemyError = MockSQLAlchemyError

# Setup UUID type for SQLAlchemy PostgreSQL
class MockUUID:
    def __init__(self, as_uuid=False, **kwargs):
        self.as_uuid = as_uuid
        self.kwargs = kwargs

sys.modules['sqlalchemy.dialects.postgresql'].UUID = MockUUID

# Setup Column type
class MockColumn:
    def __init__(self, type_=None, primary_key=False, default=None, nullable=True, **kwargs):
        self.type_ = type_
        self.primary_key = primary_key
        self.default = default
        self.nullable = nullable
        self.kwargs = kwargs

sys.modules['sqlalchemy'].Column = MockColumn

# Setup declarative_base
class MockBase:
    pass

def mock_declarative_base():
    return MockBase

sys.modules['sqlalchemy.ext.declarative'].declarative_base = mock_declarative_base

# Now import the mocked modules
import boto3
import pytest
from botocore.stub import Stubber

# Import the mocks module to access our mock implementations
from tests.mocks import (
    ValidationError, Paper, PaperDetail, Author, Category, 
    ArxivSet, PaperSearchRequest, PaginatedResponse, ErrorResponse, 
    APIResponse, get_db_connection, get_paper_by_id, search_papers, 
    get_papers_by_category, get_papers_by_date_range, get_author_by_id,
    search_authors, get_authors_by_paper, get_all_categories, 
    get_category_by_code, get_all_sets, get_set_by_code, get_set_by_id
)

# Add the project root to sys.path to make imports work
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Add the src directory to sys.path
src_dir = Path(__file__).parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Configure boto3 mock
boto3.client = MagicMock()
s3_client_mock = MagicMock()
ssm_client_mock = MagicMock()
ssm_client_mock.get_parameter.return_value = {
    'Parameter': {'Value': 'test-bucket'}
}
boto3.client.side_effect = lambda service, **kwargs: {
    's3': s3_client_mock,
    'ssm': ssm_client_mock
}.get(service, MagicMock())

# Add our mock functions to the shared.db mock module
sys.modules['shared.db'].get_db_connection = get_db_connection
sys.modules['shared.db'].get_paper_by_id = get_paper_by_id
sys.modules['shared.db'].search_papers = search_papers
sys.modules['shared.db'].get_papers_by_category = get_papers_by_category
sys.modules['shared.db'].get_papers_by_date_range = get_papers_by_date_range
sys.modules['shared.db'].get_author_by_id = get_author_by_id
sys.modules['shared.db'].search_authors = search_authors
sys.modules['shared.db'].get_authors_by_paper = get_authors_by_paper
sys.modules['shared.db'].get_all_categories = get_all_categories
sys.modules['shared.db'].get_category_by_code = get_category_by_code
sys.modules['shared.db'].get_all_sets = get_all_sets
sys.modules['shared.db'].get_set_by_code = get_set_by_code
sys.modules['shared.db'].get_set_by_id = get_set_by_id

# Add models to shared.models.schemas module
sys.modules['shared.models.schemas'].Paper = Paper
sys.modules['shared.models.schemas'].PaperDetail = PaperDetail
sys.modules['shared.models.schemas'].Author = Author
sys.modules['shared.models.schemas'].Category = Category
sys.modules['shared.models.schemas'].ArxivSet = ArxivSet
sys.modules['shared.models.schemas'].PaperSearchRequest = PaperSearchRequest
sys.modules['shared.models.schemas'].PaginatedResponse = PaginatedResponse
sys.modules['shared.models.schemas'].ErrorResponse = ErrorResponse
sys.modules['shared.models.schemas'].APIResponse = APIResponse
sys.modules['shared.models.schemas'].ValidationError = ValidationError

@pytest.fixture(autouse=True)
def mock_imports(monkeypatch):
    """Mock imports for testing Lambda functions"""
    # Create mock schemas module with all the mock classes
    class MockSchemas:
        ValidationError = ValidationError
        Paper = Paper
        PaperDetail = PaperDetail
        Author = Author
        Category = Category
        ArxivSet = ArxivSet
        PaperSearchRequest = PaperSearchRequest
        PaginatedResponse = PaginatedResponse
        ErrorResponse = ErrorResponse
        APIResponse = APIResponse
    
    # Create mock db module with all the mock functions
    class MockDB:
        get_db_connection = get_db_connection
        get_paper_by_id = get_paper_by_id
        search_papers = search_papers
        get_papers_by_category = get_papers_by_category
        get_papers_by_date_range = get_papers_by_date_range
        get_author_by_id = get_author_by_id
        search_authors = search_authors
        get_authors_by_paper = get_authors_by_paper
        get_all_categories = get_all_categories
        get_category_by_code = get_category_by_code
        get_all_sets = get_all_sets
        get_set_by_code = get_set_by_code
        get_set_by_id = get_set_by_id
        
        # Mock SQLAlchemy related functions
        def create_engine(*args, **kwargs):
            mock_engine = MagicMock()
            return mock_engine
        
        def sessionmaker(*args, **kwargs):
            mock_sessionmaker = MagicMock()
            return mock_sessionmaker
            
        def scoped_session(*args, **kwargs):
            mock_scoped_session = MagicMock()
            return mock_scoped_session
    
    # Create models module to contain schemas
    mock_models = MagicMock()
    mock_models.schemas = MockSchemas
    
    # Create shared module and assign models and db
    mock_shared = MagicMock()
    mock_shared.models = mock_models
    mock_shared.db = MockDB
    
    # Mock SQLAlchemy modules
    mock_sqlalchemy = MagicMock()
    mock_sqlalchemy_orm = MagicMock()
    mock_sqlalchemy_orm.sessionmaker = MockDB.sessionmaker
    mock_sqlalchemy_orm.scoped_session = MockDB.scoped_session
    mock_sqlalchemy.create_engine = MockDB.create_engine
    
    # Patch the imports
    monkeypatch.setitem(sys.modules, 'shared', mock_shared)
    monkeypatch.setitem(sys.modules, 'shared.models', mock_models)
    monkeypatch.setitem(sys.modules, 'shared.models.schemas', MockSchemas)
    monkeypatch.setitem(sys.modules, 'shared.db', MockDB)
    monkeypatch.setitem(sys.modules, 'sqlalchemy', mock_sqlalchemy)
    monkeypatch.setitem(sys.modules, 'sqlalchemy.orm', mock_sqlalchemy_orm)
    
    # Patch imports for Lambda-style local imports
    # This makes "from papers import X" work like "from src.papers import X"
    for module in ['papers', 'authors', 'categories', 'sets', 'abstracts']:
        mock_module = __import__(f'src.{module}', fromlist=['*'])
        monkeypatch.setitem(sys.modules, module, mock_module)
    
    # Create and patch boto3 with a mock to prevent actual AWS calls
    mock_boto3 = MagicMock()
    mock_s3_client = MagicMock()
    mock_ssm_client = MagicMock()
    
    # Configure the SSM mock to return a test bucket name
    mock_ssm_client.get_parameter.return_value = {
        'Parameter': {'Value': 'test-bucket'}
    }
    
    # Configure boto3.client to return our mocks
    mock_boto3.client.side_effect = lambda service, **kwargs: {
        's3': mock_s3_client,
        'ssm': mock_ssm_client
    }.get(service, MagicMock())
    
    # Patch boto3 at the module level
    monkeypatch.setitem(sys.modules, 'boto3', mock_boto3)


@pytest.fixture
def sample_paper_id():
    """Returns a sample paper ID"""
    return str(uuid.uuid4())


@pytest.fixture
def sample_paper():
    """Returns a sample paper object"""
    return {
        "paper_id": str(uuid.uuid4()),
        "arxiv_identifier": "2404.12345",
        "title": "Test Paper Title",
        "abstract": "This is a test abstract for testing purposes.",
        "primary_category": "CS",
        "submission_date": "2024-04-01",
        "update_date": "2024-04-02",
        "authors": [
            {"author_id": str(uuid.uuid4()), "first_name": "John", "last_name": "Doe"},
            {"author_id": str(uuid.uuid4()), "first_name": "Jane", "last_name": "Smith"}
        ],
        "categories": ["CS", "AI", "ML"]
    }


@pytest.fixture
def sample_api_event():
    """Returns a sample API Gateway event"""
    return {
        "httpMethod": "GET",
        "path": "/papers",
        "resource": "/papers",
        "queryStringParameters": {},
        "pathParameters": {},
        "headers": {
            "Accept": "application/json",
            "Content-Type": "application/json"
        },
        "body": None
    }


@pytest.fixture
def db_connection_mock():
    """Mock for database connection"""
    mock = MagicMock()
    return mock


@pytest.fixture
def s3_stub():
    """Stub for S3 client"""
    s3_client = boto3.client('s3', region_name='us-east-1')
    with Stubber(s3_client) as stubber:
        yield s3_client, stubber
        # Verify that all expected calls were made
        stubber.assert_no_pending_responses()


@pytest.fixture
def mock_ssm():
    """Mock for SSM client using patch"""
    with patch('boto3.client') as mock_client:
        ssm_mock = MagicMock()
        mock_client.return_value = ssm_mock
        ssm_mock.get_parameter.return_value = {
            'Parameter': {'Value': 'test-bucket'}
        }
        yield ssm_mock 