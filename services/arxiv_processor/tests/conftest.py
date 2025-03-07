#!/usr/bin/env python3
"""
Test configuration and fixtures for ArXiv processor
"""

import json
import os
import sys
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

# Add src to Python path for tests
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Mock os.environ.get to return test values for environment variables
original_os_environ_get = os.environ.get
def mock_os_environ_get(key, default=None):
    mock_env = {
        'ARXIV_CATEGORIES': 'cs.AI,cs.CL',
        'ARXIV_SETS': 'cs',
        'DAYS_LOOKBACK': '1',
        'BATCH_SIZE': '2',
        'API_ENDPOINT': 'http://localhost:8080'
    }
    
    return mock_env.get(key, default)

os.environ.get = mock_os_environ_get

# Replace boto3, requests, and defusedxml with mocks
sys.modules['boto3'] = MagicMock()
sys.modules['botocore'] = MagicMock()
sys.modules['botocore.exceptions'] = MagicMock()

# Mock shared package
sys.modules['shared'] = MagicMock()
sys.modules['shared.models'] = MagicMock()
sys.modules['shared.models.schemas'] = MagicMock()
sys.modules['shared.db'] = MagicMock()

# Create mocks for the shared models we need
class MockModel:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def model_dump(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

# Fix the JSON response handling for the API client test
def mockjson():
    def side_effect():
        resp = mock_response.text
        return json.loads(resp)
    
    mock_response = MagicMock()
    mock_response.json.side_effect = side_effect
    return mock_response

# Mock the shared models
sys.modules['shared.models.schemas'].Paper = MockModel
sys.modules['shared.models.schemas'].Author = MockModel
sys.modules['shared.models.schemas'].Category = MockModel
sys.modules['shared.models.schemas'].PaperAuthor = MockModel
sys.modules['shared.models.schemas'].PaperCategory = MockModel
sys.modules['shared.models.schemas'].ArxivSet = MockModel
sys.modules['shared.models.schemas'].AuthorAffiliation = MockModel
sys.modules['shared.models.schemas'].Affiliation = MockModel

# Setup ClientError mock
class MockClientError(Exception):
    pass

sys.modules['botocore.exceptions'].ClientError = MockClientError

# Sample test data
@pytest.fixture
def sample_arxiv_papers():
    """Sample ArXiv papers data"""
    return [
        {
            "identifier": "oai:arXiv.org:2301.12345",
            "abstract_url": "https://arxiv.org/abs/2301.12345",
            "authors": [
                {"first_name": "Jane", "last_name": "Doe"},
                {"first_name": "John", "last_name": "Smith"}
            ],
            "primary_category": "AI",
            "categories": ["AI", "CL"],
            "abstract": "This is a sample abstract with some LaTeX $\\alpha = \\beta$ content.",
            "title": "Sample Paper Title",
            "date": "2023-01-15",
            "publication_date": "2023-01-15T00:00:00",
            "arxiv_id": "2301.12345"
        },
        {
            "identifier": "oai:arXiv.org:2301.54321",
            "abstract_url": "https://arxiv.org/abs/2301.54321",
            "authors": [
                {"first_name": "Alice", "last_name": "Johnson"}
            ],
            "primary_category": "CL",
            "categories": ["CL"],
            "abstract": "Another sample abstract with more content.",
            "title": "Another Research Paper",
            "date": "2023-01-16",
            "publication_date": "2023-01-16T00:00:00",
            "arxiv_id": "2301.54321"
        }
    ]

@pytest.fixture
def mock_api_client():
    """Mock API client for testing"""
    with patch('src.api_client.ApiClient') as mock:
        mock_instance = mock.return_value
        
        # Set up mock responses
        mock_instance.check_paper_exists.return_value = False
        mock_instance.get_paper_id.return_value = str(uuid.uuid4())
        mock_instance.create_paper.return_value = {"paper_id": str(uuid.uuid4())}
        mock_instance.update_paper.return_value = {"paper_id": str(uuid.uuid4())}
        mock_instance.upload_abstract.return_value = {"s3_key": "abstracts/test"}
        
        yield mock_instance

@pytest.fixture
def mock_config():
    """Mock configuration"""
    with patch('src.config.ProcessorConfig') as mock:
        mock_instance = mock.return_value
        
        # Set up configuration properties
        mock_instance.arxiv_categories = ['cs.AI', 'cs.CL']
        mock_instance.arxiv_sets = ['cs']
        mock_instance.days_lookback = 1
        mock_instance.batch_size = 2
        mock_instance.api_endpoint = 'http://localhost:8080'
        
        yield mock_instance

@pytest.fixture
def mock_requests_get():
    """Mock requests.get for testing"""
    with patch('requests.get') as mock:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <OAI-PMH>
            <ListRecords>
                <record>
                    <header>
                        <identifier>oai:arXiv.org:2301.12345</identifier>
                    </header>
                    <metadata>
                        <dc:identifier>https://arxiv.org/abs/2301.12345</dc:identifier>
                        <dc:title>Sample Paper Title</dc:title>
                        <dc:description>This is a sample abstract.</dc:description>
                        <dc:creator>Doe, Jane</dc:creator>
                        <dc:creator>Smith, John</dc:creator>
                        <dc:subject>Computer Science - Artifical Intelligence</dc:subject>
                        <dc:date>2023-01-15</dc:date>
                    </metadata>
                </record>
            </ListRecords>
        </OAI-PMH>
        """
        mock_response.content = mock_response.text.encode('utf-8')
        mock.return_value = mock_response
        yield mock

@pytest.fixture
def mock_process_papers():
    """Mock process_papers function for testing"""
    with patch('src.paper_processor.process_papers') as mock:
        mock.return_value = {
            "papers": [MagicMock()],
            "authors": [MagicMock()],
            "categories": [MagicMock()],
            "paper_authors": [MagicMock()],
            "paper_categories": [MagicMock()],
            "abstracts": [{"paper_id": str(uuid.uuid4()), "abstract": "Test abstract"}]
        }
        yield mock

@pytest.fixture
def mock_fetch_papers():
    """Mock fetch_papers_for_date_range function for testing"""
    with patch('src.arxiv_fetcher.fetch_papers_for_date_range') as mock:
        mock.return_value = [
            {
                "identifier": "oai:arXiv.org:2301.12345",
                "abstract_url": "https://arxiv.org/abs/2301.12345",
                "authors": [
                    {"first_name": "Jane", "last_name": "Doe"},
                    {"first_name": "John", "last_name": "Smith"}
                ],
                "primary_category": "AI",
                "categories": ["AI", "CL"],
                "abstract": "This is a sample abstract.",
                "title": "Sample Paper Title",
                "date": "2023-01-15",
                "publication_date": "2023-01-15T00:00:00",
                "arxiv_id": "2301.12345"
            }
        ]
        yield mock 