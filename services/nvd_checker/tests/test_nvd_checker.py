import json
import os
import sys
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, patch
import pytest

# Set test environment variables
os.environ["CONFIG_PATH"] = "/test"

# ----- Helper Classes for Fakes -----

class FakeSSM:
    def __init__(self, config=None):
        self.config = config or {
            'nvd_api_key': 'test_api_key',
            'monitored_systems': {
                'vendor1': {'criticality': 'high', 'products': ['product1', 'product2']},
                'vendor2': {'criticality': 'medium', 'products': ['product3']}
            },
            's3_bucket': 'test-bucket'
        }
    
    def get_parameters(self, Names, WithDecryption=True):
        return {
            'Parameters': [
                {'Name': f"{os.environ['CONFIG_PATH']}/nvd/nvd_api_key", 'Value': self.config['nvd_api_key']},
                {'Name': f"{os.environ['CONFIG_PATH']}/nvd/monitored_systems", 'Value': json.dumps(self.config['monitored_systems'])},
                {'Name': f"{os.environ['CONFIG_PATH']}/nvd/s3_bucket", 'Value': self.config['s3_bucket']}
            ]
        }

class FakeS3:
    def __init__(self):
        self.uploaded = {}
    
    def upload_fileobj(self, Fileobj, Bucket, Key):
        self.uploaded[Key] = Fileobj.read()

# Create fake boto3
fake_boto3 = Mock()
fake_boto3.client = lambda service: FakeSSM() if service == 'ssm' else FakeS3()

# Create fake requests
fake_requests = Mock()
fake_requests.get = Mock()
fake_requests.exceptions = type('Exceptions', (), {
    'RequestException': Exception,
    'JSONDecodeError': Exception
})

# Install fake modules
sys.modules['boto3'] = fake_boto3
sys.modules['requests'] = fake_requests

# Import after setting up fakes
from src.nvd_checker import NVDChecker, main

# ----- Tests -----

def test_init_with_valid_config():
    """Test NVDChecker initialization with valid configuration"""
    checker = NVDChecker()
    assert checker.api_key == 'test_api_key'
    assert checker.systems == {
        'vendor1': {'criticality': 'high', 'products': ['product1', 'product2']},
        'vendor2': {'criticality': 'medium', 'products': ['product3']}
    }
    assert checker.s3_bucket == 'test-bucket'
    assert checker.base_url == "https://services.nvd.nist.gov/rest/json/cves/2.0"
    assert checker.headers == {
        "apiKey": 'test_api_key',
        "User-Agent": "AtomikLabs-VulnChecker/1.0"
    }

def test_get_config_error():
    """Test error handling in _get_config when SSM fails"""
    original_client = fake_boto3.client
    try:
        fake_ssm = FakeSSM()
        fake_ssm.get_parameters = Mock(side_effect=Exception("SSM Error"))
        fake_boto3.client = lambda service: fake_ssm if service == 'ssm' else FakeS3()
        
        with pytest.raises(Exception) as exc_info:
            NVDChecker()
        assert str(exc_info.value) == "SSM Error"
    finally:
        fake_boto3.client = original_client

def test_get_last_modified_date():
    """Test get_last_modified_date returns correct format"""
    checker = NVDChecker()
    with patch('src.nvd_checker.datetime') as mock_datetime:
        mock_now = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        
        expected_date = (mock_now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.000")
        result = checker.get_last_modified_date()
        
        assert result == expected_date

def test_search_vulnerabilities_success():
    """Test successful vulnerability search"""
    checker = NVDChecker()
    fake_requests.get.return_value = Mock(
        json=lambda: {
            "vulnerabilities": [{
                "cve": {
                    "id": "CVE-2024-1234",
                    "descriptions": [{"value": "Test vulnerability"}],
                    "metrics": {
                        "cvssMetricV31": [{
                            "cvssData": {
                                "baseScore": 7.5,
                                "baseSeverity": "HIGH"
                            }
                        }]
                    }
                }
            }]
        },
        raise_for_status=lambda: None
    )
    
    findings = checker.search_vulnerabilities()
    
    assert 'vendor1' in findings
    assert findings['vendor1']['criticality'] == 'high'
    assert len(findings['vendor1']['vulnerabilities']) == 2  # One for each product
    assert findings['vendor1']['vulnerabilities'][0]['id'] == 'CVE-2024-1234'

def test_search_vulnerabilities_request_error():
    """Test error handling in search_vulnerabilities when request fails"""
    checker = NVDChecker()
    fake_requests.get.side_effect = fake_requests.exceptions.RequestException("API Error")
    
    findings = checker.search_vulnerabilities()
    
    assert 'vendor1' in findings
    assert findings['vendor1']['criticality'] == 'high'
    assert len(findings['vendor1']['vulnerabilities']) == 0

def test_generate_report_success():
    """Test successful report generation"""
    checker = NVDChecker()
    findings = {
        'vendor1': {
            'criticality': 'high',
            'vulnerabilities': [{
                'id': 'CVE-2024-1234',
                'description': 'Test vulnerability',
                'metrics': {
                    'baseScore': 7.5,
                    'baseSeverity': 'HIGH'
                },
                'product': 'product1'
            }]
        }
    }
    
    with patch('src.nvd_checker.Document') as mock_document:
        mock_doc = Mock()
        mock_document.return_value = mock_doc
        mock_doc.add_heading.return_value = Mock()
        mock_doc.add_paragraph.return_value = Mock()
        
        s3_key = checker.generate_report(findings)
        
        assert mock_doc.add_heading.called
        assert mock_doc.add_paragraph.called
        assert s3_key.startswith('reports/daily/')
        assert s3_key.endswith('/nvd_vulnerabilities.docx')

def test_generate_report_s3_error():
    """Test error handling in generate_report when S3 upload fails"""
    original_client = fake_boto3.client
    try:
        # Create a new FakeS3 instance for each test
        fake_s3 = FakeS3()
        fake_s3.upload_fileobj = Mock(side_effect=Exception("S3 Error"))
        
        # Ensure we're using a new function to avoid any caching
        def mock_client(service):
            if service == 'ssm':
                return FakeSSM()
            elif service == 's3':
                return fake_s3
            return Mock()
            
        fake_boto3.client = mock_client
        
        # Create checker after setting up the mock
        checker = NVDChecker()
        findings = {
            'vendor1': {
                'criticality': 'high',
                'vulnerabilities': [{
                    'id': 'CVE-2024-1234',
                    'description': 'Test vulnerability',
                    'metrics': {
                        'baseScore': 7.5,
                        'baseSeverity': 'HIGH'
                    },
                    'product': 'product1'
                }]
            }
        }
        
        with patch('src.nvd_checker.Document'):
            with pytest.raises(Exception) as exc_info:
                checker.generate_report(findings)
            assert str(exc_info.value) == "S3 Error"
    finally:
        fake_boto3.client = original_client

def test_main_success():
    """Test successful execution of main function"""
    mock_checker = Mock()
    mock_checker.search_vulnerabilities.return_value = {"test": "findings"}
    mock_checker.generate_report.return_value = "test/s3/key"
    
    with patch('src.nvd_checker.NVDChecker', return_value=mock_checker):
        result = main()
        
        assert result['statusCode'] == 200
        assert result['body'] == 'Success'
        assert result['s3_key'] == 'test/s3/key'

def test_main_error():
    """Test error handling in main function"""
    with patch('src.nvd_checker.NVDChecker', side_effect=Exception("Test Error")):
        result = main()
        
        assert result['statusCode'] == 500
        assert result['body'] == 'Internal server error'
        assert result['error'] == 'Test Error' 