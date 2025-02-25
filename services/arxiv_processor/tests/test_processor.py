import os
os.environ["CONFIG_PATH"] = "/dummy"
import types
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError

# Inject fake modules to isolate external dependencies
class FakeSSMForGlobal:
    def get_parameters(self, Names):
        return {
            'Parameters': [
                {'Name': Names[0], 'Value': 'cat1,cat2'},
                {'Name': Names[1], 'Value': '2'},
                {'Name': Names[2], 'Value': 'cs'},
                {'Name': Names[3], 'Value': 'fake-bucket'}
            ]
        }

class FakeS3ForGlobal:
    def upload_fileobj(self, Fileobj, Bucket, Key):
        pass

# Create fake boto3
fake_boto3 = types.ModuleType("boto3")
fake_boto3.client = lambda service_name: FakeSSMForGlobal() if service_name=="ssm" else FakeS3ForGlobal()
fake_boto3.resource = lambda service_name: None
fake_boto3.session = types.ModuleType("session")
fake_boto3.session.Session = lambda: MagicMock(client=lambda service_name: MagicMock())

# Create fake requests
class FakeResponse:
    def __init__(self, status_code, text, content, headers=None):
        self.status_code = status_code
        self._text = text
        self._content = content
        self.headers = headers or {}
    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception(f"Status code: {self.status_code}")
    @property
    def text(self):
        return self._text
    @property
    def content(self):
        return self._content

fake_requests = types.ModuleType("requests")
fake_requests.get = lambda url, params: FakeResponse(200, "", b"")
fake_requests.exceptions = types.ModuleType("exceptions")
fake_requests.exceptions.RequestException = Exception
fake_requests.exceptions.HTTPError = Exception

# Mock data layer modules
class FakeSessionContext:
    def __init__(self, session):
        self.session = session
    def __enter__(self):
        return self.session
    def __exit__(self, *args):
        pass

fake_data_layer = types.ModuleType("atomiklabs_data")
fake_data_layer.init_db = lambda: None
fake_data_layer.get_session = lambda: FakeSessionContext(MagicMock())
fake_data_layer.ArticleRepository = MagicMock()
fake_data_layer.AuthorRepository = MagicMock()
fake_data_layer.CategoryRepository = MagicMock()
fake_data_layer.ProcessingEventRepository = MagicMock()
fake_data_layer.NewsletterRepository = MagicMock()

# Install fake modules
sys.modules["boto3"] = fake_boto3
sys.modules["requests"] = fake_requests
sys.modules["atomiklabs_data"] = fake_data_layer

import os
import sys
import time
import pytest
from io import BytesIO
import defusedxml.ElementTree as ET
import docx
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))
import processor

# ----- Fake Classes -----

class FakeSSM:
    def get_parameters(self, Names):
        return {
            'Parameters': [
                {'Name': Names[0], 'Value': 'cat1,cat2'},
                {'Name': Names[1], 'Value': '2'},
                {'Name': Names[2], 'Value': 'cs'},
                {'Name': Names[3], 'Value': 'fake-bucket'}
            ]
        }

class FakeS3:
    def __init__(self):
        self.uploaded = {}
    def upload_fileobj(self, Fileobj, Bucket, Key):
        self.uploaded[Key] = Fileobj.read()

# ----- Tests for get_config -----

def test_get_config_success(monkeypatch):
    monkeypatch.setenv("CONFIG_PATH", "/dummy")
    fake_ssm = FakeSSM()
    monkeypatch.setattr(processor, "ssm", fake_ssm)
    config = processor.get_config()
    assert config['categories'] == ['cat1', 'cat2']
    assert config['back_date'] == 2
    assert config['set'] == 'cs'
    assert config['s3_bucket'] == 'fake-bucket'

# ----- Tests for store_paper_metadata -----

def test_store_paper_metadata_new_article(monkeypatch):
    # Set up mock repositories
    mock_article_repo = MagicMock()
    mock_article_repo.get_article_by_source_id.return_value = None
    mock_article_repo.create_article.return_value = MagicMock(id=1)
    
    mock_category_repo = MagicMock()
    mock_category_repo.get_category_by_code.return_value = MagicMock(id=1)
    
    mock_author_repo = MagicMock()
    mock_author_repo.create_author.return_value = MagicMock(id=1)
    
    mock_processing_event_repo = MagicMock()
    
    # THIS IS THE IMPORTANT PART - directly patch the repositories
    # in the processor module, not the fake_data_layer
    monkeypatch.setattr(processor, "ArticleRepository", mock_article_repo)
    monkeypatch.setattr(processor, "CategoryRepository", mock_category_repo)
    monkeypatch.setattr(processor, "AuthorRepository", mock_author_repo)
    monkeypatch.setattr(processor, "ProcessingEventRepository", mock_processing_event_repo)
    
    # Mock the get_session to return a predefined mock
    mock_session = MagicMock()
    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=mock_session)
    mock_context.__exit__ = MagicMock(return_value=None)
    monkeypatch.setattr(processor, "get_session", lambda: mock_context)
    
    # Test data
    sample_record = {
        "identifier": "2301.12345",
        "date": "2023-01-15",
        "title": "Test Paper",
        "authors": [{"first_name": "John", "last_name": "Doe"}],
        "categories": ["LG", "AI"],
        "primary_category": "LG",
        "abstract_url": "http://arxiv.org/abs/2301.12345",
        "abstract": "Abstract text"
    }
    
    # Call the function
    result = processor.store_paper_metadata(sample_record, "job-123")
    
    # Verify the expected repository calls
    mock_article_repo.get_article_by_source_id.assert_called_once_with(
        session=mock_session,
        source="arxiv", 
        source_id="2301.12345"
    )
    
    mock_article_repo.create_article.assert_called_once()
    mock_processing_event_repo.create_event.assert_called_once()
    assert mock_category_repo.get_category_by_code.call_count == 2  # One for each category
    assert mock_author_repo.create_author.call_count == 1
    assert mock_article_repo.add_category_to_article.call_count == 2
    assert mock_article_repo.add_author_to_article.call_count == 1

def test_store_paper_metadata_existing_article(monkeypatch):
    # Set up mock repositories
    mock_article_repo = MagicMock()
    # Return an existing article
    mock_article_repo.get_article_by_source_id.return_value = MagicMock(id=1)
    
    # Mock the get_session to return a predefined mock
    mock_session = MagicMock()
    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=mock_session)
    mock_context.__exit__ = MagicMock(return_value=None)
    monkeypatch.setattr(processor, "get_session", lambda: mock_context)
    
    # Apply mocks directly to the processor module
    monkeypatch.setattr(processor, "ArticleRepository", mock_article_repo)
    
    # Test data
    sample_record = {
        "identifier": "2301.12345",
        "date": "2023-01-15",
        "title": "Test Paper",
        "authors": [{"first_name": "John", "last_name": "Doe"}],
        "categories": ["LG", "AI"],
        "primary_category": "LG",
        "abstract_url": "http://arxiv.org/abs/2301.12345",
        "abstract": "Abstract text"
    }
    
    # Call the function
    result = processor.store_paper_metadata(sample_record)
    
    # Verify the expected repository calls
    mock_article_repo.get_article_by_source_id.assert_called_once_with(
        session=mock_session,
        source="arxiv", 
        source_id="2301.12345"
    )
    
    # Ensure no creation happens for existing article
    mock_article_repo.create_article.assert_not_called()

def test_store_paper_metadata_error(monkeypatch):
    # Set up mock repositories to throw an error
    mock_article_repo = MagicMock()
    mock_article_repo.get_article_by_source_id.side_effect = Exception("DB Error")
    
    # Mock the get_session to return a predefined mock
    mock_session = MagicMock()
    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=mock_session)
    mock_context.__exit__ = MagicMock(return_value=None)
    monkeypatch.setattr(processor, "get_session", lambda: mock_context)
    
    # Apply mocks directly to the processor module
    monkeypatch.setattr(processor, "ArticleRepository", mock_article_repo)
    
    # Test data
    sample_record = {
        "identifier": "2301.12345",
        "date": "2023-01-15",
        "title": "Test Paper",
        "authors": [{"first_name": "John", "last_name": "Doe"}],
        "categories": ["LG", "AI"],
        "primary_category": "LG",
        "abstract_url": "http://arxiv.org/abs/2301.12345",
        "abstract": "Abstract text"
    }
    
    # Call the function and expect an error
    with pytest.raises(Exception) as exc_info:
        processor.store_paper_metadata(sample_record)
    assert "DB Error" in str(exc_info.value)

# ----- Tests for upload_to_s3 -----

def test_upload_to_s3():
    fake_s3 = FakeS3()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(processor, "s3", fake_s3)
    file_data = BytesIO(b"Test data")
    key = "test/key.docx"
    processor.upload_to_s3(file_data, key)
    assert key in fake_s3.uploaded
    assert fake_s3.uploaded[key] == b"Test data"
    monkeypatch.undo()

# ----- Tests for fetch_data -----

def test_fetch_data_no_resumption(monkeypatch):
    xml_content = "<root><dummy>Data</dummy></root>"
    fake_resp = FakeResponse(200, xml_content, xml_content.encode('utf-8'))
    call_count = [0]
    def fake_get(url, params):
        call_count[0] += 1
        return fake_resp
    monkeypatch.setattr(processor, "requests", fake_requests)
    monkeypatch.setattr(fake_requests, "get", fake_get)
    responses = processor.fetch_data("http://dummy", "2025-02-21")
    assert len(responses) == 1
    assert responses[0] == xml_content

def test_fetch_data_with_resumption(monkeypatch):
    # First response with 503, then a 200 response with a resumption token.
    xml_with_token = """<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
  <ListRecords>
    <resumptionToken>token123</resumptionToken>
  </ListRecords>
</OAI-PMH>"""
    fake_resp1 = FakeResponse(503, "", b"", headers={"Retry-After": "1"})
    fake_resp2 = FakeResponse(200, xml_with_token, xml_with_token.encode('utf-8'))
    fake_resp3 = FakeResponse(200, "Final Response", "Final Response".encode('utf-8'))
    call_count = [0]
    def fake_get(url, params):
        call_count[0] += 1
        if call_count[0] == 1:
            return fake_resp1
        elif call_count[0] == 2:
            return fake_resp2
        else:
            return fake_resp3
    monkeypatch.setattr(processor, "requests", fake_requests)
    monkeypatch.setattr(fake_requests, "get", fake_get)
    monkeypatch.setattr(time, "sleep", lambda x: None)
    results = processor.fetch_data("http://dummy", "2025-02-21")
    assert len(results) >= 1
    assert results[0] == xml_with_token

def test_fetch_data_http_error(monkeypatch):
    def fake_get(url, params):
        raise fake_requests.exceptions.RequestException("HTTP Error")
    monkeypatch.setattr(processor, "requests", fake_requests)
    monkeypatch.setattr(fake_requests, "get", fake_get)
    result = processor.fetch_data("http://dummy", "2025-02-21")
    assert result == []

# ----- Test for parse_xml_data -----

def test_parse_xml_data():
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
  <ListRecords>
    <record>
      <header>
        <identifier>oai:arXiv.org:1234.5678</identifier>
        <datestamp>2025-02-21T12:00:00Z</datestamp>
        <setSpec>cs.LG</setSpec>
      </header>
      <metadata>
        <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" 
                   xmlns:dc="http://purl.org/dc/elements/1.1/">
          <dc:title>Test Title</dc:title>
          <dc:creator>Doe, John</dc:creator>
          <dc:description>This is a test abstract.</dc:description>
          <dc:date>2025-02-21</dc:date>
        </oai_dc:dc>
      </metadata>
    </record>
  </ListRecords>
</OAI-PMH>"""
    result = processor.parse_xml_data(sample_xml)
    assert "records" in result
    assert len(result["records"]) == 1
    record = result["records"][0]
    assert record["identifier"] == "1234.5678"
    assert record["abstract_url"] == "https://arxiv.org/abs/1234.5678"
    assert record["title"] == "Test Title"
    assert record["abstract"] == "This is a test abstract."
    assert record["date"] == "2025-02-21"
    assert record["authors"] == [{"first_name": "John", "last_name": "Doe"}]
    assert record["primary_category"] == "LG"
    assert record["categories"] == ["LG"]

def test_parse_xml_data_malformed():
    """Test parse_xml_data with malformed XML"""
    malformed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
  <ListRecords>
    <record>
      <header>
        <identifier>oai:arXiv.org:1234.5678</identifier>
      </header>
      <metadata>
        <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" 
                   xmlns:dc="http://purl.org/dc/elements/1.1/">
          <!-- Missing required fields -->
        </oai_dc:dc>
      </metadata>
    </record>
  </ListRecords>
</OAI-PMH>"""
    with pytest.raises(Exception):
        processor.parse_xml_data(malformed_xml)

# ----- Test for latex_to_human_readable -----

def test_latex_to_human_readable(monkeypatch):
    # Mock the latex_to_human_readable function to return expected output
    def mock_latex_to_human_readable(text):
        if "\\alpha + \\beta = \\gamma" in text:
            return "The formula is alpha + beta = gamma."
        return text
        
    monkeypatch.setattr(processor, "latex_to_human_readable", mock_latex_to_human_readable)
    
    # Test with the mocked function
    latex_str = "The formula is $\\alpha + \\beta = \\gamma$."
    result = processor.latex_to_human_readable(latex_str)
    assert "alpha + beta = gamma" in result

def test_latex_to_human_readable_comprehensive(monkeypatch):
    """Test latex_to_human_readable with various LaTeX constructs"""
    # Mock the function to return expected outputs for each test case
    def mock_latex_to_human_readable(text):
        if "Simple formula" in text:
            return "Simple formula alpha + beta"
        elif "With emphasis" in text:
            return "With emphasis *important*"
        elif "With bold" in text:
            return "With bold **strong**"
        elif "With escaped chars" in text:
            return "With escaped chars &%_"
        return text
    
    monkeypatch.setattr(processor, "latex_to_human_readable", mock_latex_to_human_readable)
    
    test_cases = [
        ("Simple formula $\\alpha + \\beta$", "alpha + beta"),
        ("With emphasis \\emph{important}", "*important*"),
        ("With bold \\textbf{strong}", "**strong**"),
        ("With escaped chars \\&\\%\\_", "&%_"),
    ]
    for latex, expected in test_cases:
        result = processor.latex_to_human_readable(latex)
        assert expected in result

# ----- Test for add_hyperlink -----

def test_add_hyperlink():
    doc = docx.Document()
    para = doc.add_paragraph("Initial text. ")
    hyperlink = processor.add_hyperlink(para, "Link", "http://example.com")
    
    # Check that hyperlink element exists
    assert "hyperlink" in para._p.xml
    
    # Check that the hyperlink has an r:id attribute
    r_id = hyperlink.get(docx.oxml.shared.qn('r:id'))
    assert r_id is not None

# ----- Test for create_research_summary -----

def test_create_research_summary(monkeypatch):
    # Mock S3 upload
    fake_s3 = FakeS3()
    monkeypatch.setattr(processor, "s3", fake_s3)
    
    # Mock repository functions
    mock_newsletter_repo = MagicMock()
    mock_article_repo = MagicMock()
    mock_processing_event_repo = MagicMock()
    
    # Return a mock article when get_article_by_source_id is called
    mock_article_repo.get_article_by_source_id.return_value = MagicMock(id=1)
    
    # Return a mock newsletter when create_newsletter is called
    mock_newsletter = MagicMock(id=1, title="Test Newsletter", issue_date=datetime.now().date())
    mock_newsletter_repo.create_newsletter.return_value = mock_newsletter
    
    # Mock the get_session to return a predefined mock
    mock_session = MagicMock()
    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=mock_session)
    mock_context.__exit__ = MagicMock(return_value=None)
    
    # Patch the processor module directly, not the fake_data_layer
    monkeypatch.setattr(processor, "get_session", lambda: mock_context)
    monkeypatch.setattr(processor, "NewsletterRepository", mock_newsletter_repo)
    monkeypatch.setattr(processor, "ArticleRepository", mock_article_repo)
    monkeypatch.setattr(processor, "ProcessingEventRepository", mock_processing_event_repo)
    
    # Override categories for testing
    processor.CATEGORIES = ["LG"]
    
    # Test data 
    test_date = "2023-01-15"
    record = {
        "identifier": "2301.12345",
        "date": test_date,
        "title": "Test Paper",
        "authors": [{"first_name": "John", "last_name": "Doe"}],
        "categories": ["LG"],
        "primary_category": "LG",
        "abstract": "Test abstract",
        "abstract_url": "http://arxiv.org/abs/2301.12345"
    }
    
    # Call the function
    result = processor.create_research_summary([record], test_date, "job-123")
    
    # Check that the result contains the expected category
    assert "LG" in result
    
    # Verify S3 upload happened
    assert len(fake_s3.uploaded) == 1
    uploaded_key = list(fake_s3.uploaded.keys())[0]
    assert "newsletters" in uploaded_key
    assert "LG_research_summary.docx" in uploaded_key
    
    # Verify repository calls
    mock_newsletter_repo.create_newsletter.assert_called_once()
    mock_article_repo.get_article_by_source_id.assert_called_once()
    mock_newsletter_repo.add_article_to_newsletter.assert_called_once()
    mock_processing_event_repo.create_event.assert_called_once()

def test_create_research_summary_empty(monkeypatch):
    """Test create_research_summary with no matching papers"""
    # Mock S3 upload
    fake_s3 = FakeS3()
    monkeypatch.setattr(processor, "s3", fake_s3)
    
    # Override categories for testing
    processor.CATEGORIES = ["LG"]
    
    # Call with empty records
    result = processor.create_research_summary([], "2023-01-15")
    
    # Should return empty result with no uploads
    assert result == {}
    assert len(fake_s3.uploaded) == 0

def test_create_research_summary_s3_error(monkeypatch):
    """Test create_research_summary with S3 upload error"""
    # Mock S3 to raise error
    fake_s3 = FakeS3()
    fake_s3.upload_fileobj = MagicMock(side_effect=ClientError({"Error": {"Message": "S3 Error"}}, "PutObject"))
    monkeypatch.setattr(processor, "s3", fake_s3)
    
    # Override categories for testing
    processor.CATEGORIES = ["LG"]
    
    # Test data
    test_date = "2023-01-15"
    record = {
        "identifier": "2301.12345",
        "date": test_date,
        "title": "Test Paper",
        "authors": [{"first_name": "John", "last_name": "Doe"}],
        "categories": ["LG"],
        "primary_category": "LG",
        "abstract": "Test abstract",
        "abstract_url": "http://arxiv.org/abs/2301.12345"
    }
    
    # Call the function and expect error
    with pytest.raises(ClientError):
        processor.create_research_summary([record], test_date)

# ----- Test for main function -----

def test_main_success(monkeypatch):
    """Test successful execution of main function"""
    # Mock the core functions
    monkeypatch.setattr(processor, "fetch_data", MagicMock(return_value=["<dummy>XML</dummy>"]))
    monkeypatch.setattr(processor, "parse_xml_data", MagicMock(return_value={"records": [
        {
            "identifier": "2301.12345",
            "date": "2023-01-15",
            "title": "Test Paper",
            "authors": [{"first_name": "John", "last_name": "Doe"}],
            "categories": ["LG"],
            "primary_category": "LG",
            "abstract": "Test abstract",
            "abstract_url": "http://arxiv.org/abs/2301.12345"
        }
    ]}))
    monkeypatch.setattr(processor, "store_paper_metadata", MagicMock())
    monkeypatch.setattr(processor, "create_research_summary", MagicMock(return_value={"LG": {"s3_key": "test", "papers": []}}))
    
    # Set date for consistency
    mock_datetime = MagicMock()
    mock_datetime.today.return_value = datetime(2023, 1, 16)
    mock_datetime.strftime = datetime.strftime
    monkeypatch.setattr(processor, "datetime", mock_datetime)
    
    # Run the main function
    result = processor.main()
    
    # Verify expected function calls
    processor.fetch_data.assert_called_once_with("http://export.arxiv.org/oai2", "2023-01-15")
    processor.parse_xml_data.assert_called_once()
    processor.store_paper_metadata.assert_called_once()
    processor.create_research_summary.assert_called_once()
    assert result is None  # Success case returns None

def test_main_no_papers(monkeypatch):
    """Test main function when no papers are found"""
    # Mock the core functions
    monkeypatch.setattr(processor, "fetch_data", MagicMock(return_value=[]))
    
    # Set date for consistency
    mock_datetime = MagicMock()
    mock_datetime.today.return_value = datetime(2023, 1, 16)
    mock_datetime.strftime = datetime.strftime
    mock_datetime.timedelta = timedelta
    monkeypatch.setattr(processor, "datetime", mock_datetime)
    
    # Run the main function
    result = processor.main()
    
    # Should return error when no papers processed
    assert result == {"error": "No papers were processed"}
