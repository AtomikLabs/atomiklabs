"""
Unit tests for the abstracts module
"""
import json
import os
import uuid
from unittest.mock import patch, MagicMock

import pytest
from botocore.exceptions import ClientError

from src.abstracts import (
    get_s3_bucket_name,
    _build_response,
    handle_error,
    get_abstract_s3_key,
    get_abstract_handler,
    store_abstract_handler,
    delete_abstract_handler,
    lambda_handler
)


def test_get_abstract_s3_key():
    """Test the get_abstract_s3_key function"""
    # Test with standard arXiv identifier
    paper_id = str(uuid.uuid4())
    arxiv_id = "2404.12345"
    set_code = "CS"
    
    key = get_abstract_s3_key(paper_id, arxiv_id, set_code)
    assert key == f"abstracts/{set_code}/2024/04/{arxiv_id}.txt"
    
    # Test with non-standard identifier
    arxiv_id = "invalid-id"
    key = get_abstract_s3_key(paper_id, arxiv_id, set_code)
    assert key == f"abstracts/{set_code}/other/{paper_id}.txt"


@patch("src.abstracts.os.environ.get")
@patch("src.abstracts.boto3.client")
def test_get_s3_bucket_name_success(mock_boto3_client, mock_environ_get):
    """Test get_s3_bucket_name when successful"""
    # Setup mocks
    ssm_mock = MagicMock()
    mock_boto3_client.return_value = ssm_mock
    mock_environ_get.return_value = "/test/path"
    
    ssm_mock.get_parameter.return_value = {
        'Parameter': {'Value': 'test-bucket'}
    }
    
    # Call function
    bucket_name = get_s3_bucket_name()
    
    # Verify result
    assert bucket_name == 'test-bucket'
    
    # Verify mocks were called correctly
    mock_boto3_client.assert_called_once_with('ssm')
    ssm_mock.get_parameter.assert_called_once_with(
        Name="/test/path/s3_bucket",
        WithDecryption=False
    )


@patch("src.abstracts.os.environ.get")
@patch("src.abstracts.boto3.client")
def test_get_s3_bucket_name_error(mock_boto3_client, mock_environ_get):
    """Test get_s3_bucket_name when SSM fails"""
    # Setup mocks
    ssm_mock = MagicMock()
    mock_boto3_client.return_value = ssm_mock
    mock_environ_get.return_value = "/test/path"
    
    # Make the SSM call raise an error
    ssm_mock.get_parameter.side_effect = ClientError(
        {'Error': {'Code': 'ParameterNotFound'}},
        'GetParameter'
    )
    
    # Call function and expect exception
    with pytest.raises(RuntimeError) as excinfo:
        get_s3_bucket_name()
    
    # Verify the error message
    assert "Failed to retrieve S3 bucket name" in str(excinfo.value)


@patch("src.abstracts.get_db_connection")
@patch("src.abstracts.get_paper_by_id")
@patch("src.abstracts.get_abstract_s3_key")
@patch("src.abstracts.s3_client")
@patch("src.abstracts.s3_bucket", "test-bucket")
def test_get_abstract_handler_success(mock_s3_client, mock_get_s3_key, mock_get_paper_by_id, 
                                      mock_get_db_connection, sample_api_event, db_connection_mock):
    """Test get_abstract_handler for successful retrieval"""
    # Setup mocks
    mock_get_db_connection.return_value.__enter__.return_value = db_connection_mock
    
    paper_mock = MagicMock()
    paper_mock.arxiv_identifier = "2404.12345"
    paper_mock.primary_category = "CS"
    mock_get_paper_by_id.return_value = paper_mock
    
    mock_get_s3_key.return_value = "abstracts/CS/2024/04/2404.12345.txt"
    
    s3_response_mock = {
        'Body': MagicMock()
    }
    s3_response_mock['Body'].read.return_value = b"This is a test abstract"
    mock_s3_client.get_object.return_value = s3_response_mock
    
    # Setup event
    paper_id = str(uuid.uuid4())
    sample_api_event["pathParameters"] = {"id": paper_id}
    
    # Call handler
    response = get_abstract_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["abstract"] == "This is a test abstract"
    assert body["paper_id"] == paper_id
    
    # Verify mocks were called correctly
    mock_get_paper_by_id.assert_called_once_with(db_connection_mock, paper_id)
    mock_get_s3_key.assert_called_once_with(
        paper_id=paper_id,
        arxiv_identifier=paper_mock.arxiv_identifier,
        set_code=paper_mock.primary_category
    )
    mock_s3_client.get_object.assert_called_once_with(
        Bucket="test-bucket",
        Key=mock_get_s3_key.return_value
    )


@patch("src.abstracts.get_db_connection")
@patch("src.abstracts.get_paper_by_id")
@patch("src.abstracts.get_abstract_s3_key")
@patch("src.abstracts.s3_client")
@patch("src.abstracts.s3_bucket", "test-bucket")
def test_get_abstract_handler_not_found(mock_s3_client, mock_get_s3_key, mock_get_paper_by_id, 
                                        mock_get_db_connection, sample_api_event, db_connection_mock):
    """Test get_abstract_handler when abstract not found in S3"""
    # Setup mocks
    mock_get_db_connection.return_value.__enter__.return_value = db_connection_mock
    
    paper_mock = MagicMock()
    paper_mock.arxiv_identifier = "2404.12345"
    paper_mock.primary_category = "CS"
    mock_get_paper_by_id.return_value = paper_mock
    
    mock_get_s3_key.return_value = "abstracts/CS/2024/04/2404.12345.txt"
    
    # Make S3 get_object raise a NoSuchKey error
    mock_s3_client.get_object.side_effect = ClientError(
        {'Error': {'Code': 'NoSuchKey'}},
        'GetObject'
    )
    
    # Setup event
    paper_id = str(uuid.uuid4())
    sample_api_event["pathParameters"] = {"id": paper_id}
    
    # Call handler
    response = get_abstract_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert body["error"] == "ABSTRACT_NOT_FOUND"


@patch("src.abstracts.get_db_connection")
@patch("src.abstracts.get_paper_by_id")
@patch("src.abstracts.get_abstract_s3_key")
@patch("src.abstracts.s3_client")
@patch("src.abstracts.s3_bucket", "test-bucket")
def test_store_abstract_handler_success(mock_s3_client, mock_get_s3_key, mock_get_paper_by_id, 
                                        mock_get_db_connection, sample_api_event, db_connection_mock):
    """Test store_abstract_handler for successful storage"""
    # Setup mocks
    mock_get_db_connection.return_value.__enter__.return_value = db_connection_mock
    
    paper_mock = MagicMock()
    paper_mock.arxiv_identifier = "2404.12345"
    paper_mock.primary_category = "CS"
    mock_get_paper_by_id.return_value = paper_mock
    
    mock_get_s3_key.return_value = "abstracts/CS/2024/04/2404.12345.txt"
    
    # Setup event
    paper_id = str(uuid.uuid4())
    sample_api_event["pathParameters"] = {"id": paper_id}
    sample_api_event["body"] = json.dumps({"abstract": "This is a test abstract"})
    
    # Call handler
    response = store_abstract_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["message"] == "Abstract stored successfully"
    
    # Verify mocks were called correctly
    mock_s3_client.put_object.assert_called_once_with(
        Bucket="test-bucket",
        Key=mock_get_s3_key.return_value,
        Body=b"This is a test abstract",
        ContentType='text/plain'
    )


@patch("src.abstracts.get_db_connection")
@patch("src.abstracts.get_paper_by_id")
@patch("src.abstracts.get_abstract_s3_key")
@patch("src.abstracts.s3_client")
@patch("src.abstracts.s3_bucket", "test-bucket")
def test_delete_abstract_handler_success(mock_s3_client, mock_get_s3_key, mock_get_paper_by_id, 
                                         mock_get_db_connection, sample_api_event, db_connection_mock):
    """Test delete_abstract_handler for successful deletion"""
    # Setup mocks
    mock_get_db_connection.return_value.__enter__.return_value = db_connection_mock
    
    paper_mock = MagicMock()
    paper_mock.arxiv_identifier = "2404.12345"
    paper_mock.primary_category = "CS"
    mock_get_paper_by_id.return_value = paper_mock
    
    mock_get_s3_key.return_value = "abstracts/CS/2024/04/2404.12345.txt"
    
    # Setup event
    paper_id = str(uuid.uuid4())
    sample_api_event["pathParameters"] = {"id": paper_id}
    
    # Call handler
    response = delete_abstract_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["message"] == "Abstract deleted successfully"
    
    # Verify mocks were called correctly
    mock_s3_client.head_object.assert_called_once_with(
        Bucket="test-bucket",
        Key=mock_get_s3_key.return_value
    )
    mock_s3_client.delete_object.assert_called_once_with(
        Bucket="test-bucket",
        Key=mock_get_s3_key.return_value
    )


@patch("src.abstracts.get_abstract_handler")
@patch("src.abstracts.store_abstract_handler")
@patch("src.abstracts.delete_abstract_handler")
def test_lambda_handler_routing(mock_delete_handler, mock_store_handler, mock_get_handler, sample_api_event):
    """Test the lambda_handler function for routing to the correct handler"""
    # Setup the event for different HTTP methods and resources
    sample_api_event["resource"] = "/papers/{id}/abstract"
    
    # Test GET
    sample_api_event["httpMethod"] = "GET"
    lambda_handler(sample_api_event, {})
    mock_get_handler.assert_called_once_with(sample_api_event, {})
    mock_get_handler.reset_mock()
    
    # Test PUT
    sample_api_event["httpMethod"] = "PUT"
    lambda_handler(sample_api_event, {})
    mock_store_handler.assert_called_once_with(sample_api_event, {})
    mock_store_handler.reset_mock()
    
    # Test DELETE
    sample_api_event["httpMethod"] = "DELETE"
    lambda_handler(sample_api_event, {})
    mock_delete_handler.assert_called_once_with(sample_api_event, {})
    mock_delete_handler.reset_mock()
    
    # Test method not allowed
    sample_api_event["httpMethod"] = "POST"
    response = lambda_handler(sample_api_event, {})
    assert response["statusCode"] == 405 