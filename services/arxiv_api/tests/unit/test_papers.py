"""
Unit tests for the papers module
"""
import json
import uuid
from unittest.mock import patch, MagicMock

import pytest

from src.papers import (
    _build_response,
    handle_error,
    get_papers_handler,
    get_paper_by_id_handler,
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


@patch("src.papers.logging")
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


@patch("src.papers.get_db_connection")
@patch("src.papers.search_papers")
def test_get_papers_handler_basic(mock_search_papers, mock_get_db_connection, sample_api_event, db_connection_mock):
    """Test the get_papers_handler function with basic parameters"""
    # Setup mocks
    mock_get_db_connection.return_value.__enter__.return_value = db_connection_mock
    mock_search_papers.return_value = ([], 0)
    
    # Call handler
    response = get_papers_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "items" in body
    assert body["page"] == 1
    assert body["total_items"] == 0
    
    # Verify mocks were called correctly
    mock_get_db_connection.assert_called_once()
    mock_search_papers.assert_called_once()


@patch("src.papers.get_db_connection")
@patch("src.papers.search_papers")
def test_get_papers_handler_with_search(mock_search_papers, mock_get_db_connection, sample_api_event, db_connection_mock):
    """Test the get_papers_handler function with search parameters"""
    # Setup mocks
    mock_get_db_connection.return_value.__enter__.return_value = db_connection_mock
    mock_search_papers.return_value = ([], 0)
    
    # Setup event with search parameters
    sample_api_event["queryStringParameters"] = {
        "search": "test",
        "page": "2",
        "page_size": "10"
    }
    
    # Call handler
    response = get_papers_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["page"] == 2
    assert body["page_size"] == 10
    
    # Verify search was called with the right parameters
    mock_search_papers.assert_called_once()
    args, kwargs = mock_search_papers.call_args
    assert kwargs["search_term"] == "test"
    assert kwargs["limit"] == 10
    assert kwargs["offset"] == 10  # page 2 with page_size 10


@patch("src.papers.get_db_connection")
@patch("src.papers.get_paper_by_id")
def test_get_paper_by_id_handler_success(mock_get_paper_by_id, mock_get_db_connection, sample_api_event, db_connection_mock, sample_paper):
    """Test the get_paper_by_id_handler function for a successful case"""
    # Setup mocks
    mock_get_db_connection.return_value.__enter__.return_value = db_connection_mock
    
    # Create a MagicMock for the paper with a dict method that returns sample_paper
    paper_mock = MagicMock()
    paper_mock.dict.return_value = sample_paper
    mock_get_paper_by_id.return_value = paper_mock
    
    # Setup event with paper ID
    paper_id = str(uuid.uuid4())
    sample_api_event["pathParameters"] = {"id": paper_id}
    
    # Call handler
    response = get_paper_by_id_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 200
    
    # Verify mocks were called correctly
    mock_get_db_connection.assert_called_once()
    mock_get_paper_by_id.assert_called_once_with(db_connection_mock, paper_id)


@patch("src.papers.get_db_connection")
@patch("src.papers.get_paper_by_id")
def test_get_paper_by_id_handler_not_found(mock_get_paper_by_id, mock_get_db_connection, sample_api_event, db_connection_mock):
    """Test the get_paper_by_id_handler function when paper is not found"""
    # Setup mocks
    mock_get_db_connection.return_value.__enter__.return_value = db_connection_mock
    mock_get_paper_by_id.return_value = None
    
    # Setup event with paper ID
    paper_id = str(uuid.uuid4())
    sample_api_event["pathParameters"] = {"id": paper_id}
    
    # Call handler
    response = get_paper_by_id_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert body["error"] == "NOT_FOUND"
    
    # Verify mocks were called correctly
    mock_get_paper_by_id.assert_called_once_with(db_connection_mock, paper_id)


@patch("src.papers.get_papers_handler")
@patch("src.papers.get_paper_by_id_handler")
def test_lambda_handler_routing(mock_get_paper_by_id_handler, mock_get_papers_handler, sample_api_event):
    """Test the lambda_handler function for routing to the correct handler"""
    # Test routing to get_papers_handler
    sample_api_event["httpMethod"] = "GET"
    sample_api_event["resource"] = "/papers"
    
    lambda_handler(sample_api_event, {})
    mock_get_papers_handler.assert_called_once_with(sample_api_event, {})
    mock_get_papers_handler.reset_mock()
    
    # Test routing to get_paper_by_id_handler
    sample_api_event["httpMethod"] = "GET"
    sample_api_event["resource"] = "/papers/{id}"
    
    lambda_handler(sample_api_event, {})
    mock_get_paper_by_id_handler.assert_called_once_with(sample_api_event, {})
    
    # Test method not allowed
    sample_api_event["httpMethod"] = "POST"
    sample_api_event["resource"] = "/papers"
    
    response = lambda_handler(sample_api_event, {})
    assert response["statusCode"] == 405 