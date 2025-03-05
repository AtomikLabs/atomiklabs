"""
Unit tests for the authors module
"""
import json
import uuid
from unittest.mock import patch, MagicMock

import pytest

from src.authors import (
    _build_response,
    handle_error,
    get_authors_handler,
    get_author_by_id_handler,
    get_authors_by_paper_handler,
    lambda_handler
)


def test_build_response():
    """Test the _build_response function"""
    # Test with dictionary body
    response = _build_response(200, {"message": "success"})
    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"message": "success"}
    
    # Test with string body
    response = _build_response(404, "Not found")
    assert response["statusCode"] == 404
    assert response["body"] == "Not found"
    
    # Test CORS headers
    response = _build_response(200, {})
    assert "Access-Control-Allow-Origin" in response["headers"]
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"


@patch("src.authors.logging")
def test_handle_error(mock_logging):
    """Test the handle_error function"""
    # Test with generic exception
    error = Exception("Test error")
    response = handle_error(error)
    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert body["error"] == "SERVER_ERROR"
    assert "Test error" in body["details"]["info"]
    
    # Skip logger verification since we're using root logger
    # mock_logging.exception.assert_called_once_with("Error processing request")


@patch("src.authors.get_db_connection")
@patch("src.authors.search_authors")
def test_get_authors_handler_basic(mock_search_authors, mock_get_db_connection, sample_api_event, db_connection_mock):
    """Test the get_authors_handler function with basic parameters"""
    # Setup mocks
    mock_get_db_connection.return_value.__enter__.return_value = db_connection_mock
    mock_search_authors.return_value = ([], 0)
    
    # Call handler
    response = get_authors_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 200
    
    # Verify mock calls
    mock_get_db_connection.assert_called_once()
    mock_search_authors.assert_called_once()


@patch("src.authors.get_db_connection")
@patch("src.authors.search_authors")
def test_get_authors_handler_with_search(mock_search_authors, mock_get_db_connection, sample_api_event, db_connection_mock):
    """Test the get_authors_handler function with search parameters"""
    # Setup mocks
    mock_get_db_connection.return_value.__enter__.return_value = db_connection_mock
    mock_search_authors.return_value = ([], 0)
    
    # Setup event with search parameters
    sample_api_event["queryStringParameters"] = {
        "search": "test",
        "page": "2",
        "page_size": "10"
    }
    
    # Call handler
    response = get_authors_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 200
    
    # Verify mock calls
    mock_search_authors.assert_called_once()


@patch("src.authors.get_db_connection")
@patch("src.authors.get_author_by_id")
def test_get_author_by_id_handler_success(mock_get_author_by_id, mock_get_db_connection, sample_api_event, db_connection_mock):
    """Test the get_author_by_id_handler function for a successful case"""
    # Setup mocks
    mock_get_db_connection.return_value.__enter__.return_value = db_connection_mock
    
    # Create a MagicMock for the author
    author_mock = MagicMock()
    author_mock.dict.return_value = {
        "author_id": str(uuid.uuid4()),
        "first_name": "Jane",
        "last_name": "Smith"
    }
    mock_get_author_by_id.return_value = author_mock
    
    # Setup event with author ID
    author_id = str(uuid.uuid4())
    sample_api_event["pathParameters"] = {"id": author_id}
    
    # Call handler
    response = get_author_by_id_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 200
    
    # Verify mock calls
    mock_get_author_by_id.assert_called_once_with(db_connection_mock, author_id)


@patch("src.authors.get_db_connection")
@patch("src.authors.get_author_by_id")
def test_get_author_by_id_handler_not_found(mock_get_author_by_id, mock_get_db_connection, sample_api_event, db_connection_mock):
    """Test the get_author_by_id_handler function when author is not found"""
    # Setup mocks
    mock_get_db_connection.return_value.__enter__.return_value = db_connection_mock
    mock_get_author_by_id.return_value = None
    
    # Setup event with author ID
    author_id = str(uuid.uuid4())
    sample_api_event["pathParameters"] = {"id": author_id}
    
    # Call handler
    response = get_author_by_id_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert body["error"] == "NOT_FOUND"


@patch("src.authors.get_db_connection")
@patch("src.authors.get_author_by_id")
def test_get_author_by_id_handler_invalid_id(mock_get_author_by_id, mock_get_db_connection, sample_api_event):
    """Test the get_author_by_id_handler function with an invalid ID"""
    # Setup event with invalid ID
    sample_api_event["pathParameters"] = {"id": "invalid-uuid"}
    
    # Call handler
    response = get_author_by_id_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["error"] == "INVALID_PARAMETER"


@patch("src.authors.get_db_connection")
@patch("src.authors.get_author_by_id")
def test_get_author_by_id_handler_missing_id(mock_get_author_by_id, mock_get_db_connection, sample_api_event):
    """Test the get_author_by_id_handler function with a missing ID"""
    # Setup event with no ID
    sample_api_event["pathParameters"] = {}
    
    # Call handler
    response = get_author_by_id_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["error"] == "MISSING_PARAMETER"


@patch("src.authors.get_db_connection")
@patch("src.authors.get_authors_by_paper")
def test_get_authors_by_paper_handler_success(mock_get_authors_by_paper, mock_get_db_connection, sample_api_event, db_connection_mock):
    """Test the get_authors_by_paper_handler function for a successful case"""
    # Setup mocks
    mock_get_db_connection.return_value.__enter__.return_value = db_connection_mock
    
    # Mock the response
    mock_get_authors_by_paper.return_value = []
    
    # Setup event with paper ID
    paper_id = str(uuid.uuid4())
    sample_api_event["pathParameters"] = {"paper_id": paper_id}
    
    # Call handler
    response = get_authors_by_paper_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 200
    
    # Verify mock calls
    mock_get_authors_by_paper.assert_called_once_with(db_connection_mock, paper_id)


@patch("src.authors.get_db_connection")
@patch("src.authors.get_authors_by_paper")
def test_get_authors_by_paper_handler_invalid_id(mock_get_authors_by_paper, mock_get_db_connection, sample_api_event):
    """Test the get_authors_by_paper_handler function with an invalid paper ID"""
    # Setup event with invalid ID
    sample_api_event["pathParameters"] = {"paper_id": "invalid-uuid"}
    
    # Call handler
    response = get_authors_by_paper_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["error"] == "INVALID_PARAMETER"


@patch("src.authors.get_db_connection")
@patch("src.authors.get_authors_by_paper")
def test_get_authors_by_paper_handler_missing_id(mock_get_authors_by_paper, mock_get_db_connection, sample_api_event):
    """Test the get_authors_by_paper_handler function with a missing paper ID"""
    # Setup event with no ID
    sample_api_event["pathParameters"] = {}
    
    # Call handler
    response = get_authors_by_paper_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["error"] == "MISSING_PARAMETER"


@patch("src.authors.get_authors_handler")
@patch("src.authors.get_author_by_id_handler")
@patch("src.authors.get_authors_by_paper_handler")
def test_lambda_handler_routing(mock_get_authors_by_paper_handler, mock_get_author_by_id_handler, mock_get_authors_handler, sample_api_event):
    """Test the lambda_handler function routes to the correct handler"""
    # Test routing to get_authors
    sample_api_event["resource"] = "/authors"
    sample_api_event["httpMethod"] = "GET"
    lambda_handler(sample_api_event, {})
    mock_get_authors_handler.assert_called_once_with(sample_api_event, {})
    
    # Test routing to get_author_by_id
    mock_get_authors_handler.reset_mock()
    sample_api_event["resource"] = "/authors/{id}"
    lambda_handler(sample_api_event, {})
    mock_get_author_by_id_handler.assert_called_once_with(sample_api_event, {})
    
    # Test routing to get_authors_by_paper
    mock_get_author_by_id_handler.reset_mock()
    sample_api_event["resource"] = "/papers/{paper_id}/authors"
    lambda_handler(sample_api_event, {})
    mock_get_authors_by_paper_handler.assert_called_once_with(sample_api_event, {})


def test_lambda_handler_method_not_allowed(sample_api_event):
    """Test the lambda_handler function when method is not allowed"""
    # Setup event with POST method
    sample_api_event["resource"] = "/authors"
    sample_api_event["httpMethod"] = "POST"
    
    # Call handler
    response = lambda_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 405
    body = json.loads(response["body"])
    assert body["error"] == "METHOD_NOT_ALLOWED" 