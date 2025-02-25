import os
import sys
import pytest
from botocore.exceptions import ClientError
import datetime
from zoneinfo import ZoneInfo
from unittest.mock import Mock, patch, MagicMock

# Set up the Python path to handle both individual test runs and combined test runs
test_dir = os.path.dirname(os.path.abspath(__file__))
mailer_dir = os.path.dirname(test_dir)
if mailer_dir not in sys.path:
    sys.path.insert(0, mailer_dir)

# Create mock data layer components
class MockSession:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass

# Mock the data layer before importing the mailer module
sys.modules['atomiklabs_data'] = MagicMock()
sys.modules['atomiklabs_data'].init_db = MagicMock()
sys.modules['atomiklabs_data'].get_session = MagicMock(return_value=MockSession())
sys.modules['atomiklabs_data'].NewsletterRepository = MagicMock()
sys.modules['atomiklabs_data'].EmailRepository = MagicMock()

# Now import the mailer module - using a more robust import path
try:
    # Try the direct import first (when running tests individually)
    from src.mailer import get_config, send_email_with_attachments, get_s3_files, lambda_handler, get_newsletters_for_date
except ModuleNotFoundError:
    # Fall back to the full path (when running combined tests)
    from services.arxiv_mailer.src.mailer import get_config, send_email_with_attachments, get_s3_files, lambda_handler, get_newsletters_for_date

# ----- Helper Classes for Fakes -----

class FakeBody:
    def __init__(self, key):
        self.data = key.encode('utf-8')
    def read(self):
        return self.data

class FakeSSM:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
    def get_parameters(self, Names):
        if self.should_fail:
            raise ClientError({'Error': {'Message': 'SSM failure'}}, 'get_parameters')
        return {
            'Parameters': [
                {'Name': Names[0], 'Value': 'my_bucket'},
                {'Name': Names[1], 'Value': 'sender@example.com,recipient@example.com'},
                {'Name': Names[2], 'Value': '2'},
            ]
        }

class FakeSES:
    def __init__(self, should_fail=False):
        self.called = False
        self.should_fail = should_fail
    def send_raw_email(self, Source, Destinations, RawMessage):
        self.called = True
        self.source = Source
        self.destinations = Destinations
        self.raw_message = RawMessage
        if self.should_fail:
            raise ClientError({'Error': {'Message': 'Sending failed'}}, 'send_raw_email')
        return {'MessageId': '12345'}

class FakeS3:
    def __init__(self, contents=None, should_fail=False):
        self.contents = contents or {}
        self.should_fail = should_fail
    def list_objects_v2(self, Bucket, Prefix):
        if self.should_fail:
            raise ClientError({'Error': {'Message': 'S3 failure'}}, 'list_objects_v2')
        return self.contents.get(Prefix, {})
    def get_object(self, Bucket, Key):
        if self.should_fail:
            raise ClientError({'Error': {'Message': 'S3 failure'}}, 'get_object')
        return {'Body': FakeBody(Key)}

# ----- Tests -----

def test_get_config():
    """Test the get_config function."""
    # Set up the environment variable
    os.environ["CONFIG_PATH"] = "/test/path"
    
    # Create a fake SSM client
    ssm_client = FakeSSM()
    
    # Call the function
    config = get_config(ssm_client)
    
    # Check the results
    assert config['s3_bucket'] == 'my_bucket'
    assert config['recipients'] == ['sender@example.com', 'recipient@example.com']
    assert config['back_date'] == 2

def test_get_config_missing_env():
    """Test the get_config function with missing environment variable."""
    # Delete the environment variable if it exists
    if "CONFIG_PATH" in os.environ:
        del os.environ["CONFIG_PATH"]
    
    # Create a fake SSM client
    ssm_client = FakeSSM()
    
    # Call the function and check for exception
    with pytest.raises(ValueError, match="CONFIG_PATH environment variable is required"):
        get_config(ssm_client)

def test_get_config_client_error():
    """Test the get_config function with a client error."""
    # Set up the environment variable
    os.environ["CONFIG_PATH"] = "/test/path"
    
    # Create a fake SSM client that fails
    ssm_client = FakeSSM(should_fail=True)
    
    # Call the function and check for exception
    with pytest.raises(ClientError):
        get_config(ssm_client)

def test_send_email():
    """Test the send_email_with_attachments function."""
    # Create a fake SES client
    ses_client = FakeSES()
    
    # Define test values
    recipients = ['test@example.com']
    subject = 'Test Subject'
    body = 'Test body'
    attachments = [{'data': b'test data', 'filename': 'test.txt'}]
    
    # Call the function
    result = send_email_with_attachments(ses_client, recipients, subject, body, attachments)
    
    # Check that the call was made
    assert ses_client.called
    assert ses_client.source == 'test@example.com'
    assert ses_client.destinations == recipients
    # For a real test, we would check more about the message content
    assert result is None  # No database record created

def test_send_email_with_newsletter_id():
    """Test the send_email_with_attachments function with a newsletter ID."""
    # Create a fake SES client
    ses_client = FakeSES()
    
    # Mock the EmailRepository
    mock_email = MagicMock(id=123)
    sys.modules['atomiklabs_data'].EmailRepository.create_email.return_value = mock_email
    
    # Define test values
    recipients = ['test@example.com']
    subject = 'Test Subject'
    body = 'Test body'
    attachments = [{'data': b'test data', 'filename': 'test.txt'}]
    newsletter_id = 456
    
    # Call the function
    result = send_email_with_attachments(ses_client, recipients, subject, body, attachments, newsletter_id)
    
    # Check that the call was made
    assert ses_client.called
    assert ses_client.source == 'test@example.com'
    assert ses_client.destinations == recipients
    
    # Check database record creation
    sys.modules['atomiklabs_data'].init_db.assert_called_once()
    sys.modules['atomiklabs_data'].EmailRepository.create_email.assert_called_once()
    assert sys.modules['atomiklabs_data'].EmailRepository.create_email.call_args[1]['newsletter_id'] == newsletter_id
    assert result == 123  # Email ID is returned

def test_send_email_error():
    """Test the send_email_with_attachments function with an error."""
    # Create a fake SES client that fails
    ses_client = FakeSES(should_fail=True)
    
    # Define test values
    recipients = ['test@example.com']
    subject = 'Test Subject'
    body = 'Test body'
    attachments = [{'data': b'test data', 'filename': 'test.txt'}]
    
    # Call the function and check for exception
    with pytest.raises(ClientError):
        send_email_with_attachments(ses_client, recipients, subject, body, attachments)

def test_get_s3_files():
    """Test the get_s3_files function."""
    # Create a fake S3 client with some test data
    s3_client = FakeS3({
        'test_prefix/': {
            'Contents': [
                {'Key': 'test_prefix/file1.txt'},
                {'Key': 'test_prefix/file2.txt'}
            ]
        }
    })
    
    # Call the function
    files = get_s3_files(s3_client, 'test_bucket', 'test_prefix/')
    
    # Check the results
    assert len(files) == 2
    assert files[0]['filename'] == 'file1.txt'
    assert files[0]['s3_key'] == 'test_prefix/file1.txt'
    assert files[1]['filename'] == 'file2.txt'
    assert files[1]['s3_key'] == 'test_prefix/file2.txt'

def test_get_s3_files_no_files():
    """Test the get_s3_files function with no files."""
    # Create a fake S3 client with no contents
    s3_client = FakeS3()
    
    # Call the function
    files = get_s3_files(s3_client, 'test_bucket', 'empty_prefix/')
    
    # Check the results
    assert len(files) == 0

def test_get_s3_files_error():
    """Test the get_s3_files function with an error."""
    # Create a fake S3 client that fails
    s3_client = FakeS3(should_fail=True)
    
    # Call the function
    files = get_s3_files(s3_client, 'test_bucket', 'test_prefix/')
    
    # Check the results - it should return an empty list
    assert len(files) == 0

def test_get_newsletters_for_date():
    """Test the get_newsletters_for_date function."""
    # Mock the NewsletterRepository
    mock_newsletter = MagicMock(id=123, title='Test Newsletter', s3_path='test/path')
    sys.modules['atomiklabs_data'].NewsletterRepository.get_newsletter_by_date.return_value = mock_newsletter
    
    # Reset init_db call counter
    sys.modules['atomiklabs_data'].init_db.reset_mock()
    
    # Call the function
    test_date = datetime.date(2023, 1, 15)
    newsletters = get_newsletters_for_date(test_date)
    
    # Check the results
    assert len(newsletters) == 1
    assert newsletters[0].id == 123
    assert newsletters[0].title == 'Test Newsletter'
    
    # Verify init_db was called
    sys.modules['atomiklabs_data'].init_db.assert_called_once()
    
    # Check that the repository method was called with the right parameters
    call_args = sys.modules['atomiklabs_data'].NewsletterRepository.get_newsletter_by_date.call_args
    assert call_args[1]['issue_date'] == test_date

def test_get_newsletters_for_date_exception():
    """Test the get_newsletters_for_date function when an exception occurs."""
    # Mock the init_db to raise an exception
    sys.modules['atomiklabs_data'].init_db.side_effect = Exception("Database connection failed")
    
    # Call the function
    test_date = datetime.date(2023, 1, 15)
    newsletters = get_newsletters_for_date(test_date)
    
    # Check the results - should return empty list when exception occurs
    assert len(newsletters) == 0
    
    # Reset the init_db mock for other tests
    sys.modules['atomiklabs_data'].init_db.reset_mock()
    sys.modules['atomiklabs_data'].init_db.side_effect = None

def test_get_newsletters_for_date_none_found():
    """Test the get_newsletters_for_date function when no newsletters are found."""
    # Mock the NewsletterRepository to return None
    sys.modules['atomiklabs_data'].NewsletterRepository.get_newsletter_by_date.return_value = None
    
    # Reset init_db call counter
    sys.modules['atomiklabs_data'].init_db.reset_mock()
    
    # Call the function
    test_date = datetime.date(2023, 1, 15)
    newsletters = get_newsletters_for_date(test_date)
    
    # Check the results
    assert len(newsletters) == 0
    
    # Verify init_db was called
    sys.modules['atomiklabs_data'].init_db.assert_called_once()

def test_lambda_handler():
    """Test the lambda_handler function."""
    # Mock SSM client
    mock_ssm = FakeSSM()
    
    # Mock S3 client with test data
    mock_s3 = FakeS3({
        'newsletters/2023-01-14/': {
            'Contents': [
                {'Key': 'newsletters/2023-01-14/LG_research_summary.docx'},
                {'Key': 'newsletters/2023-01-14/AI_research_summary.docx'}
            ]
        }
    })
    
    # Mock SES client
    mock_ses = FakeSES()
    
    # Mock boto3.client to return our mock clients
    def mock_boto3_client(service_name):
        if service_name == 'ssm':
            return mock_ssm
        elif service_name == 's3':
            return mock_s3
        elif service_name == 'ses':
            return mock_ses
        else:
            raise ValueError(f"Unexpected service name: {service_name}")
    
    # Mock the date
    mock_now = datetime.datetime(2023, 1, 16, 10, 0, 0, tzinfo=ZoneInfo('America/Los_Angeles'))
    
    # Mock the NewsletterRepository
    mock_newsletter = MagicMock(
        id=123, 
        title='Test Newsletter', 
        s3_path='newsletters/2023-01-14/LG_research_summary.docx'
    )
    sys.modules['atomiklabs_data'].NewsletterRepository.get_newsletter_by_date.return_value = mock_newsletter
    
    # Mock the EmailRepository
    mock_email = MagicMock(id=456)
    sys.modules['atomiklabs_data'].EmailRepository.create_email.return_value = mock_email
    
    # Set CONFIG_PATH in environment
    os.environ["CONFIG_PATH"] = "/test/path"
    
    # Get the import path for the datetime patch
    # This handles both local and combined test runs
    datetime_import_path = lambda_handler.__module__ + ".datetime"
    
    # Call the lambda_handler function
    with patch('boto3.client', mock_boto3_client), \
         patch(datetime_import_path) as mock_datetime:
        
        # Configure the mock datetime
        mock_datetime.now.return_value = mock_now
        mock_datetime.strftime = datetime.datetime.strftime
        mock_datetime.strptime = datetime.datetime.strptime
        
        result = lambda_handler({}, {})
    
    # Check results
    assert mock_ses.called
    assert result['statusCode'] == 200
    assert 'emailId' in result
    assert result['emailId'] == 456

def test_lambda_handler_no_files():
    """Test the lambda_handler function with no files found."""
    # Mock SSM client
    mock_ssm = FakeSSM()
    
    # Mock S3 client with no files
    mock_s3 = FakeS3()
    
    # Mock SES client
    mock_ses = FakeSES()
    
    # Mock boto3.client to return our mock clients
    def mock_boto3_client(service_name):
        if service_name == 'ssm':
            return mock_ssm
        elif service_name == 's3':
            return mock_s3
        elif service_name == 'ses':
            return mock_ses
        else:
            raise ValueError(f"Unexpected service name: {service_name}")
    
    # Mock the date
    mock_now = datetime.datetime(2023, 1, 16, 10, 0, 0, tzinfo=ZoneInfo('America/Los_Angeles'))
    
    # Mock the NewsletterRepository to return None
    sys.modules['atomiklabs_data'].NewsletterRepository.get_newsletter_by_date.return_value = None
    
    # Set CONFIG_PATH in environment
    os.environ["CONFIG_PATH"] = "/test/path"
    
    # Get the import path for the datetime patch
    # This handles both local and combined test runs
    datetime_import_path = lambda_handler.__module__ + ".datetime"
    
    # Call the lambda_handler function
    with patch('boto3.client', mock_boto3_client), \
         patch(datetime_import_path) as mock_datetime:
        
        # Configure the mock datetime
        mock_datetime.now.return_value = mock_now
        mock_datetime.strftime = datetime.datetime.strftime
        mock_datetime.strptime = datetime.datetime.strptime
        
        result = lambda_handler({}, {})
    
    # Check results
    assert not mock_ses.called
    assert result['statusCode'] == 200
    assert result['body'] == 'No reports to send'

def test_lambda_handler_with_multiple_newsletters():
    """Test the lambda_handler function with multiple newsletters."""
    # Mock SSM client
    mock_ssm = FakeSSM()
    
    # Mock S3 client with test data
    mock_s3 = FakeS3({
        'newsletters/2023-01-14/': {
            'Contents': [
                {'Key': 'newsletters/2023-01-14/LG_research_summary.docx'},
                {'Key': 'newsletters/2023-01-14/AI_research_summary.docx'}
            ]
        }
    })
    
    # Mock SES client
    mock_ses = FakeSES()
    
    # Mock boto3.client to return our mock clients
    def mock_boto3_client(service_name):
        if service_name == 'ssm':
            return mock_ssm
        elif service_name == 's3':
            return mock_s3
        elif service_name == 'ses':
            return mock_ses
        else:
            raise ValueError(f"Unexpected service name: {service_name}")
    
    # Mock the date
    mock_now = datetime.datetime(2023, 1, 16, 10, 0, 0, tzinfo=ZoneInfo('America/Los_Angeles'))
    
    # Mock the NewsletterRepository to return multiple newsletters
    mock_newsletter1 = MagicMock(
        id=123, 
        title='Machine Learning Research Summary', 
        s3_path='newsletters/2023-01-14/LG_research_summary.docx'
    )
    mock_newsletter2 = MagicMock(
        id=124, 
        title='AI Research Summary', 
        s3_path='newsletters/2023-01-14/AI_research_summary.docx'
    )
    
    # Need to patch the get_newsletters_for_date function since we can't easily modify
    # NewsletterRepository.get_newsletter_by_date to return multiple objects
    
    # Mock the EmailRepository
    mock_email = MagicMock(id=456)
    sys.modules['atomiklabs_data'].EmailRepository.create_email.return_value = mock_email
    
    # Set CONFIG_PATH in environment
    os.environ["CONFIG_PATH"] = "/test/path"
    
    # Get the import paths for patches
    # This handles both local and combined test runs
    datetime_import_path = lambda_handler.__module__ + ".datetime"
    get_newsletters_import_path = lambda_handler.__module__ + ".get_newsletters_for_date"
    
    # Call the lambda_handler function
    with patch('boto3.client', mock_boto3_client), \
         patch(datetime_import_path) as mock_datetime, \
         patch(get_newsletters_import_path, return_value=[mock_newsletter1, mock_newsletter2]):
        
        # Configure the mock datetime
        mock_datetime.now.return_value = mock_now
        mock_datetime.strftime = datetime.datetime.strftime
        mock_datetime.strptime = datetime.datetime.strptime
        
        result = lambda_handler({}, {})
    
    # Check results
    assert mock_ses.called
    assert result['statusCode'] == 200
    assert 'emailId' in result
    assert result['emailId'] == 456
    
    # Check that the email body would contain both newsletter titles
    email_data = mock_ses.raw_message['Data']
    assert 'Machine Learning Research Summary' in email_data
    assert 'AI Research Summary' in email_data
