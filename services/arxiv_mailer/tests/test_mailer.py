import datetime
import os
import sys
from unittest.mock import MagicMock, Mock, patch
from zoneinfo import ZoneInfo

import pytest
from botocore.exceptions import ClientError

# Ensure the src directory is in sys.path for imports.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

# First patch boto3 to prevent any real AWS calls during import
with patch("boto3.client", MagicMock()), patch("boto3.session", MagicMock()):
    from src.mailer import get_config, get_s3_files, lambda_handler, send_email_with_attachments

# ----- Helper Classes for Fakes -----


class FakeBody:
    def __init__(self, key):
        self.data = key.encode("utf-8")

    def read(self):
        return self.data


class FakeSSM:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail

    def get_parameters(self, Names):
        if self.should_fail:
            raise ClientError({"Error": {"Message": "SSM failure"}}, "get_parameters")
        return {
            "Parameters": [
                {"Name": Names[0], "Value": "my_bucket"},
                {"Name": Names[1], "Value": "sender@example.com,recipient@example.com"},
                {"Name": Names[2], "Value": "2"},
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
            raise ClientError({"Error": {"Message": "Sending failed"}}, "send_raw_email")
        return {"MessageId": "12345"}


class FakeS3:
    def __init__(self, contents=None, should_fail=False):
        # contents is a dict mapping prefix to a dict mimicking list_objects_v2 output.
        # e.g., { "dummy/": { "Contents": [ { "Key": "dummy/file1.txt" }, ... ] } }
        self.contents = contents or {}
        self.should_fail = should_fail

    def list_objects_v2(self, Bucket, Prefix):
        if self.should_fail:
            raise Exception("S3 error")
        return self.contents.get(Prefix, {})

    def get_object(self, Bucket, Key):
        return {"Body": FakeBody(Key)}


# ----- Tests for get_config -----


def test_get_config():
    os.environ["CONFIG_PATH"] = "/test/path"
    mock_ssm = Mock()
    mock_ssm.get_parameters.return_value = {
        "Parameters": [
            {"Name": "/test/path/arxiv/s3_bucket", "Value": "my-bucket"},
            {"Name": "/test/path/arxiv/email/recipients", "Value": "test@example.com"},
            {"Name": "/test/path/arxiv/back_date", "Value": "7"},
        ]
    }

    config = get_config(mock_ssm)
    assert config == {"s3_bucket": "my-bucket", "recipients": ["test@example.com"], "back_date": 7}


def test_get_config_missing_env():
    if "CONFIG_PATH" in os.environ:
        del os.environ["CONFIG_PATH"]
    mock_ssm = Mock()

    with pytest.raises(ValueError) as exc:
        get_config(mock_ssm)
    assert "CONFIG_PATH environment variable is required" in str(exc.value)


def test_get_config_client_error():
    os.environ["CONFIG_PATH"] = "/test/path"
    mock_ssm = Mock()
    mock_ssm.get_parameters.side_effect = ClientError({"Error": {"Message": "SSM failure"}}, "GetParameters")

    with pytest.raises(ClientError):
        get_config(mock_ssm)


# ----- Tests for send_email_with_attachments -----


def test_send_email():
    mock_ses = Mock()
    mock_ses.send_raw_email.return_value = {"MessageId": "123"}

    send_email_with_attachments(
        ses_client=mock_ses,
        recipients=["test@example.com"],
        subject="Test",
        body="Test body",
        attachments=[{"data": b"test", "filename": "test.txt"}],
    )

    mock_ses.send_raw_email.assert_called_once()
    call_args = mock_ses.send_raw_email.call_args[1]
    assert call_args["Source"] == "test@example.com"
    assert call_args["Destinations"] == ["test@example.com"]
    assert "test.txt" in call_args["RawMessage"]["Data"]


def test_send_email_error():
    mock_ses = Mock()
    mock_ses.send_raw_email.side_effect = ClientError({"Error": {"Message": "SES failure"}}, "SendRawEmail")

    with pytest.raises(ClientError):
        send_email_with_attachments(
            ses_client=mock_ses,
            recipients=["test@example.com"],
            subject="Test",
            body="Test body",
            attachments=[{"data": b"test", "filename": "test.txt"}],
        )


# ----- Tests for get_s3_files -----


def test_get_s3_files():
    mock_s3 = Mock()
    mock_s3.list_objects_v2.return_value = {"Contents": [{"Key": "prefix/file1.txt"}, {"Key": "prefix/file2.txt"}]}
    mock_s3.get_object.return_value = {"Body": Mock(read=lambda: b"test data")}

    files = get_s3_files(mock_s3, "my-bucket", "prefix/")
    assert len(files) == 2
    assert files[0]["filename"] == "file1.txt"
    assert files[0]["data"] == b"test data"
    assert files[1]["filename"] == "file2.txt"
    assert files[1]["data"] == b"test data"


def test_get_s3_files_no_files():
    mock_s3 = Mock()
    mock_s3.list_objects_v2.return_value = {}

    files = get_s3_files(mock_s3, "my-bucket", "prefix/")
    assert files == []


def test_get_s3_files_error():
    mock_s3 = Mock()
    mock_s3.list_objects_v2.side_effect = Exception("S3 error")

    files = get_s3_files(mock_s3, "my-bucket", "prefix/")
    assert files == []


# ----- Tests for lambda_handler -----


# Patch the boto3 client creation to prevent any real AWS calls
@patch("boto3.client")
def test_lambda_handler(mock_boto3_client):
    # Setup mock clients
    mock_ssm = Mock()
    mock_s3 = Mock()
    mock_ses = Mock()

    # Configure mock_boto3_client to return our mocks
    mock_boto3_client.side_effect = lambda service, **kwargs: {"ssm": mock_ssm, "s3": mock_s3, "ses": mock_ses}[service]

    # Configure the SSM mock response
    mock_ssm.get_parameters.return_value = {
        "Parameters": [
            {"Name": "/test/path/arxiv/s3_bucket", "Value": "my-bucket"},
            {"Name": "/test/path/arxiv/email/recipients", "Value": "test@example.com"},
            {"Name": "/test/path/arxiv/back_date", "Value": "1"},
        ]
    }

    # Configure the S3 mock response for ArXiv files
    mock_s3.list_objects_v2.side_effect = lambda **kwargs: {
        # Return different responses based on the prefix
        "Contents": [{"Key": f"{kwargs['Prefix']}file1.txt"}] if "newsletters" in kwargs["Prefix"] else []
    }

    # Configure the S3 get_object response
    mock_s3.get_object.return_value = {"Body": Mock(read=lambda: b"test data")}

    # Configure the SES mock response
    mock_ses.send_raw_email.return_value = {"MessageId": "123"}

    # Set environment variable
    os.environ["CONFIG_PATH"] = "/test/path"

    # Call the function
    result = lambda_handler({}, {})

    # Verify the result
    assert result["statusCode"] == 200
    assert result["body"] == "Email sent successfully"

    # Verify that boto3.client was called with the correct services
    assert len(mock_boto3_client.call_args_list) == 3
    assert mock_boto3_client.call_args_list[0].args[0] == "ssm"
    assert mock_boto3_client.call_args_list[1].args[0] == "s3"
    assert mock_boto3_client.call_args_list[2].args[0] == "ses"

    # Verify that SES was called to send an email
    mock_ses.send_raw_email.assert_called_once()


@patch("boto3.client")
def test_lambda_handler_no_files(mock_boto3_client):
    # Setup mock clients
    mock_ssm = Mock()
    mock_s3 = Mock()
    mock_ses = Mock()

    # Configure mock_boto3_client to return our mocks
    mock_boto3_client.side_effect = lambda service, **kwargs: {"ssm": mock_ssm, "s3": mock_s3, "ses": mock_ses}[service]

    # Configure the SSM mock response
    mock_ssm.get_parameters.return_value = {
        "Parameters": [
            {"Name": "/test/path/arxiv/s3_bucket", "Value": "my-bucket"},
            {"Name": "/test/path/arxiv/email/recipients", "Value": "test@example.com"},
            {"Name": "/test/path/arxiv/back_date", "Value": "1"},
        ]
    }

    # Configure the S3 mock to return no files
    mock_s3.list_objects_v2.return_value = {}

    # Set environment variable
    os.environ["CONFIG_PATH"] = "/test/path"

    # Call the function
    result = lambda_handler({}, {})

    # Verify the result
    assert result["statusCode"] == 200
    assert result["body"] == "No reports to send"

    # Verify that SES was not called
    mock_ses.send_raw_email.assert_not_called()
