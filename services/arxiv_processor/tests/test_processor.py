import os
os.environ["CONFIG_PATH"] = "/dummy"
import types
import sys
from botocore.exceptions import ClientError

# Inject fake modules to isolate external dependencies
class FakeSSMForGlobal:
    def get_parameters(self, Names):
        return {
            'Parameters': [
                {'Name': Names[0], 'Value': 'cat1,cat2'},
                {'Name': Names[1], 'Value': '2'},
                {'Name': Names[2], 'Value': 'cs'},
                {'Name': Names[3], 'Value': 'fake-bucket'},
                {'Name': Names[4], 'Value': 'fake-table'}
            ]
        }

class FakeS3ForGlobal:
    def upload_fileobj(self, Fileobj, Bucket, Key):
        pass

class FakeDynamoForGlobal:
    def Table(self, name):
        class FakeTable:
            def put_item(self, Item):
                pass
        return FakeTable()

# Create fake boto3
fake_boto3 = types.ModuleType("boto3")
fake_boto3.client = lambda service_name: FakeSSMForGlobal() if service_name=="ssm" else FakeS3ForGlobal()
fake_boto3.resource = lambda service_name: FakeDynamoForGlobal() if service_name=="dynamodb" else None

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
fake_requests.exceptions.HTTPError = Exception

# Install fake modules
sys.modules["boto3"] = fake_boto3
sys.modules["requests"] = fake_requests

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
                {'Name': Names[3], 'Value': 'fake-bucket'},
                {'Name': Names[4], 'Value': 'fake-table'}
            ]
        }

class FakeDynamoTable:
    def __init__(self):
        self.items = []
    def put_item(self, Item):
        self.items.append(Item)

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
    assert config['dynamodb_table'] == 'fake-table'

# ----- Tests for store_paper_metadata -----

def test_store_paper_metadata():
    fake_dynamo = FakeDynamoTable()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(processor, "dynamodb", fake_dynamo)
    sample_record = {
        "identifier": "id1",
        "date": "2025-02-21",
        "title": "Test Paper",
        "authors": [{"first_name": "John", "last_name": "Doe"}],
        "categories": ["Test"],
        "primary_category": "Test",
        "abstract_url": "http://arxiv.org/abs/1234",
        "abstract": "Abstract text"
    }
    processor.store_paper_metadata(sample_record)
    assert len(fake_dynamo.items) == 1
    item = fake_dynamo.items[0]
    assert item["id"] == "id1"
    monkeypatch.undo()

def test_store_paper_metadata_error():
    """Test error handling in store_paper_metadata when DynamoDB fails"""
    fake_dynamo = FakeDynamoTable()
    fake_dynamo.put_item = lambda Item: (_ for _ in ()).throw(ClientError({"Error": {"Message": "DynamoDB Error"}}, "PutItem"))
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(processor, "dynamodb", fake_dynamo)
    sample_record = {
        "identifier": "id1",
        "date": "2025-02-21",
        "title": "Test Paper",
        "authors": [{"first_name": "John", "last_name": "Doe"}],
        "categories": ["Test"],
        "primary_category": "Test",
        "abstract_url": "http://arxiv.org/abs/1234",
        "abstract": "Abstract text"
    }
    with pytest.raises(ClientError) as exc_info:
        processor.store_paper_metadata(sample_record)
    assert "DynamoDB Error" in str(exc_info.value)
    monkeypatch.undo()

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
    fake_resp2 = FakeResponse(200, "Final Response", "Final Response".encode('utf-8'))
    call_count = [0]
    def fake_get(url, params):
        call_count[0] += 1
        if call_count[0] == 1:
            return fake_resp1
        else:
            return fake_resp2
    monkeypatch.setattr(processor, "requests", fake_requests)
    monkeypatch.setattr(fake_requests, "get", fake_get)
    monkeypatch.setattr(time, "sleep", lambda x: None)
    results = processor.fetch_data("http://dummy", "2025-02-21")
    assert len(results) >= 1

def test_fetch_data_http_error(monkeypatch):
    fake_resp = FakeResponse(404, "", b"")
    def fake_get(url, params):
        return fake_resp
    monkeypatch.setattr(processor, "requests", fake_requests)
    monkeypatch.setattr(fake_requests, "get", fake_get)
    monkeypatch.setattr(time, "sleep", lambda x: None)
    result = processor.fetch_data("http://dummy", "2025-02-21")
    assert result == []

# ----- Test for parse_xml_data -----

def test_parse_xml_data():
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
  <ListRecords>
    <record>
      <header>
        <identifier>oai:arxiv.org:1234.5678</identifier>
      </header>
      <metadata>
        <dc:identifier xmlns:dc="http://purl.org/dc/elements/1.1/">http://arxiv.org/abs/1234.5678</dc:identifier>
        <dc:title xmlns:dc="http://purl.org/dc/elements/1.1/">Test Title</dc:title>
        <dc:description xmlns:dc="http://purl.org/dc/elements/1.1/">This is a test abstract.</dc:description>
        <dc:date xmlns:dc="http://purl.org/dc/elements/1.1/">2025-02-21</dc:date>
        <dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/">Doe, John</dc:creator>
        <dc:subject xmlns:dc="http://purl.org/dc/elements/1.1/">Computer Science - Machine Learning</dc:subject>
      </metadata>
    </record>
  </ListRecords>
</OAI-PMH>"""
    result = processor.parse_xml_data(sample_xml)
    assert "records" in result
    assert len(result["records"]) == 1
    record = result["records"][0]
    assert record["identifier"] == "oai:arxiv.org:1234.5678"
    assert record["abstract_url"] == "http://arxiv.org/abs/1234.5678"
    assert record["title"] == "Test Title"
    assert record["abstract"] == "This is a test abstract."
    assert record["date"] == "2025-02-21"
    assert record["authors"] == [{"last_name": "Doe", "first_name": "John"}]
    assert record["primary_category"] == "LG"
    assert record["categories"] == ["LG"]

def test_parse_xml_data_malformed():
    """Test parse_xml_data with malformed XML"""
    malformed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
  <ListRecords>
    <record>
      <header>
        <identifier>oai:arxiv.org:1234.5678</identifier>
      </header>
      <metadata>
        <dc:identifier xmlns:dc="http://purl.org/dc/elements/1.1/">http://arxiv.org/abs/1234.5678</dc:identifier>
        <dc:title xmlns:dc="http://purl.org/dc/elements/1.1/">Test Title</dc:title>
        <dc:date xmlns:dc="http://purl.org/dc/elements/1.1/">2025-02-21</dc:date>
        <dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/">Doe, John</dc:creator>
        <dc:subject xmlns:dc="http://purl.org/dc/elements/1.1/">Computer Science - Machine Learning</dc:subject>
      </metadata>
    </record>
  </ListRecords>
</OAI-PMH>"""
    result = processor.parse_xml_data(malformed_xml)
    assert result["records"] == []

# ----- Test for latex_to_human_readable -----

def test_latex_to_human_readable():
    latex_str = "The formula is $\\alpha + \\beta = \\gamma$."
    result = processor.latex_to_human_readable(latex_str)
    assert "alpha" in result
    assert "beta" in result
    assert "gamma" in result

def test_latex_to_human_readable_comprehensive():
    """Test latex_to_human_readable with various LaTeX constructs"""
    test_cases = [
        ("Simple formula $\\alpha + \\beta$", "alpha + beta"),
        ("Multiple formulas $\\alpha$ and $\\beta$", "alpha and beta"),
        ("With symbols $\\leq \\geq \\neq$", "<= >= !="),
        ("Complex formula $\\sum_{i=1}^n \\alpha_i$", "∑ alpha"),
        ("Greek letters $\\omega \\phi \\psi$", "omega phi psi"),
        ("With braces {test}", "test"),
        ("With escaped chars \\textbf{bold}", "bold"),
    ]
    for latex, expected in test_cases:
        result = processor.latex_to_human_readable(latex)
        for exp_part in expected.split():
            assert exp_part in result

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
    
    # Check that the relationship exists and points to the correct URL
    rels = para.part.rels
    assert r_id in rels
    assert rels[r_id].target_ref == "http://example.com"
    
    # Check that the text is correct
    assert "Link" in para._p.xml

# ----- Test for create_research_summary -----

def test_create_research_summary(monkeypatch):
    uploaded_keys = []
    def fake_upload(file_data, key):
        uploaded_keys.append(key)
    monkeypatch.setattr(processor, "upload_to_s3", fake_upload)
    processor.CATEGORIES = ["Test Category"]
    test_date = "2025-02-21"
    record = {
        "identifier": "id1",
        "abstract_url": "http://arxiv.org/abs/1234",
        "authors": [{"first_name": "John", "last_name": "Doe"}],
        "primary_category": "Test Category",
        "categories": ["Test"],
        "abstract": "Test abstract",
        "title": "Test Title",
        "date": test_date
    }
    summary = processor.create_research_summary([record], test_date)
    assert any("newsletters" in key for key in uploaded_keys)
    assert "Test Category" in summary
    summary_info = summary["Test Category"]
    assert summary_info["s3_key"].endswith("Test Category_research_summary.docx")
    assert len(summary_info["papers"]) == 1

def test_create_research_summary_empty():
    """Test create_research_summary with empty findings"""
    fake_s3 = FakeS3()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(processor, "s3", fake_s3)
    date = "2025-02-21"
    result = processor.create_research_summary([], date)
    assert result == {}
    monkeypatch.undo()

def test_create_research_summary_error():
    """Test create_research_summary with S3 upload error"""
    fake_s3 = FakeS3()
    def raise_error(*args, **kwargs):
        raise ClientError({"Error": {"Message": "S3 Error"}}, "PutObject")
    fake_s3.upload_fileobj = raise_error
    
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(processor, "s3", fake_s3)
    monkeypatch.setattr(processor, "CATEGORIES", ["AI"])
    
    date = "2025-02-21"
    records = [{
        "identifier": "id1",
        "date": date,
        "title": "Test Paper",
        "authors": [{"first_name": "John", "last_name": "Doe"}],
        "categories": ["AI"],
        "primary_category": "AI",
        "abstract_url": "http://arxiv.org/abs/1234",
        "abstract": "Abstract text"
    }]
    
    with pytest.raises(ClientError) as exc_info:
        processor.create_research_summary(records, date)
    assert "S3 Error" in str(exc_info.value)
    monkeypatch.undo()

def test_main_success():
    """Test successful execution of main function"""
    # Mock successful responses
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
  <ListRecords>
    <record>
      <header><identifier>id1</identifier></header>
      <metadata>
        <dc:identifier xmlns:dc="http://purl.org/dc/elements/1.1/">http://arxiv.org/abs/1234</dc:identifier>
        <dc:title xmlns:dc="http://purl.org/dc/elements/1.1/">Test Title</dc:title>
        <dc:description xmlns:dc="http://purl.org/dc/elements/1.1/">Test Abstract</dc:description>
        <dc:date xmlns:dc="http://purl.org/dc/elements/1.1/">2025-02-21</dc:date>
        <dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/">Doe, John</dc:creator>
        <dc:subject xmlns:dc="http://purl.org/dc/elements/1.1/">Computer Science - Machine Learning</dc:subject>
      </metadata>
    </record>
  </ListRecords>
</OAI-PMH>"""
    fake_resp = FakeResponse(200, xml_content, xml_content.encode('utf-8'))
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(processor.requests, "get", lambda *args, **kwargs: fake_resp)
    monkeypatch.setattr(processor, "time", type("FakeTime", (), {"sleep": lambda x: None}))
    processor.main()
    monkeypatch.undo()

def test_main_no_papers():
    """Test main function when no papers are found"""
    # Mock empty response
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
  <ListRecords></ListRecords>
</OAI-PMH>"""
    fake_resp = FakeResponse(200, xml_content, xml_content.encode('utf-8'))
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(processor.requests, "get", lambda *args, **kwargs: fake_resp)
    monkeypatch.setattr(processor, "time", type("FakeTime", (), {"sleep": lambda x: None}))
    result = processor.main()
    assert result == {"error": "No papers were processed"}
    monkeypatch.undo()
