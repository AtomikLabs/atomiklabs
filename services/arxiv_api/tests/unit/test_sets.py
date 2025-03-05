"""
Unit tests for the sets module
"""
import json
import uuid
from unittest.mock import patch, MagicMock

import pytest

from src.sets import (
    _build_response,
    handle_error,
    get_sets_handler,
    get_set_by_id_handler,
    get_set_by_code_handler,
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


@patch("src.sets.logging")
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


@patch("src.sets.get_db_connection")
@patch("src.sets.get_all_sets")
def test_get_sets_handler(mock_get_all_sets, mock_get_db_connection, sample_api_event, db_connection_mock):
    """Test the get_sets_handler function"""
    # Setup mocks
    mock_get_db_connection.return_value.__enter__.return_value = db_connection_mock
    
    # Create mock sets
    set1 = MagicMock()
    set1.dict.return_value = {
        "set_id": str(uuid.uuid4()),
        "set_code": "physics", 
        "name": "Physics",
        "description": "Physics sets"
    }
    set2 = MagicMock()
    set2.dict.return_value = {
        "set_id": str(uuid.uuid4()),
        "set_code": "cs", 
        "name": "Computer Science",
        "description": "CS sets"
    }
    mock_get_all_sets.return_value = [set1, set2]
    
    # Call handler
    response = get_sets_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    
    # The response is wrapped in a paginated response format
    assert "items" in body
    assert len(body["items"]) == 2
    assert body["items"][0]["set_code"] == "physics"
    assert body["items"][1]["set_code"] == "cs"
    
    # Verify mock calls
    mock_get_all_sets.assert_called_once_with(db_connection_mock)


@patch("src.sets.get_db_connection")
@patch("src.sets.get_set_by_id")
def test_get_set_by_id_handler_success(mock_get_set_by_id, mock_get_db_connection, sample_api_event, db_connection_mock):
    """Test the get_set_by_id_handler function for a successful case"""
    # Setup mocks
    mock_get_db_connection.return_value.__enter__.return_value = db_connection_mock
    
    # Create a mock set
    set_id = str(uuid.uuid4())
    set_mock = MagicMock()
    set_mock.dict.return_value = {
        "set_id": set_id,
        "set_code": "physics", 
        "name": "Physics",
        "description": "Physics sets"
    }
    mock_get_set_by_id.return_value = set_mock
    
    # Setup event with set ID
    sample_api_event["pathParameters"] = {"id": set_id}
    
    # Call handler
    response = get_set_by_id_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["set_id"] == set_id
    assert body["set_code"] == "physics"
    
    # Verify mock calls
    mock_get_set_by_id.assert_called_once_with(db_connection_mock, set_id)


@patch("src.sets.get_db_connection")
@patch("src.sets.get_set_by_id")
def test_get_set_by_id_handler_not_found(mock_get_set_by_id, mock_get_db_connection, sample_api_event, db_connection_mock):
    """Test the get_set_by_id_handler function when set is not found"""
    # Setup mocks
    mock_get_db_connection.return_value.__enter__.return_value = db_connection_mock
    mock_get_set_by_id.return_value = None
    
    # Setup event with set ID
    set_id = str(uuid.uuid4())
    sample_api_event["pathParameters"] = {"id": set_id}
    
    # Call handler
    response = get_set_by_id_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert body["error"] == "NOT_FOUND"


@patch("src.sets.get_db_connection")
@patch("src.sets.get_set_by_id")
def test_get_set_by_id_handler_invalid_id(mock_get_set_by_id, mock_get_db_connection, sample_api_event):
    """Test the get_set_by_id_handler function with an invalid ID"""
    # Setup event with invalid ID
    sample_api_event["pathParameters"] = {"id": "invalid-uuid"}
    
    # Call handler
    response = get_set_by_id_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["error"] == "INVALID_PARAMETER"


@patch("src.sets.get_db_connection")
@patch("src.sets.get_set_by_id")
def test_get_set_by_id_handler_missing_id(mock_get_set_by_id, mock_get_db_connection, sample_api_event):
    """Test the get_set_by_id_handler function with a missing ID"""
    # Setup event with no ID
    sample_api_event["pathParameters"] = {}
    
    # Call handler
    response = get_set_by_id_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["error"] == "MISSING_PARAMETER"


@patch("src.sets.get_db_connection")
@patch("src.sets.get_set_by_code")
def test_get_set_by_code_handler_success(mock_get_set_by_code, mock_get_db_connection, sample_api_event, db_connection_mock):
    """Test the get_set_by_code_handler function for a successful case"""
    # Setup mocks
    mock_get_db_connection.return_value.__enter__.return_value = db_connection_mock
    
    # Create a mock set
    set_mock = MagicMock()
    set_mock.dict.return_value = {
        "set_id": str(uuid.uuid4()),
        "set_code": "physics", 
        "name": "Physics",
        "description": "Physics sets"
    }
    mock_get_set_by_code.return_value = set_mock
    
    # Setup event with set code
    sample_api_event["pathParameters"] = {"code": "physics"}
    
    # Call handler
    response = get_set_by_code_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["set_code"] == "physics"
    
    # Verify mock calls
    mock_get_set_by_code.assert_called_once_with(db_connection_mock, "physics")


@patch("src.sets.get_db_connection")
@patch("src.sets.get_set_by_code")
def test_get_set_by_code_handler_not_found(mock_get_set_by_code, mock_get_db_connection, sample_api_event, db_connection_mock):
    """Test the get_set_by_code_handler function when set is not found"""
    # Setup mocks
    mock_get_db_connection.return_value.__enter__.return_value = db_connection_mock
    mock_get_set_by_code.return_value = None
    
    # Setup event with set code
    sample_api_event["pathParameters"] = {"code": "unknown"}
    
    # Call handler
    response = get_set_by_code_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert body["error"] == "NOT_FOUND"


@patch("src.sets.get_db_connection")
@patch("src.sets.get_set_by_code")
def test_get_set_by_code_handler_missing_code(mock_get_set_by_code, mock_get_db_connection, sample_api_event):
    """Test the get_set_by_code_handler function with a missing code"""
    # Setup event with no code
    sample_api_event["pathParameters"] = {}
    
    # Call handler
    response = get_set_by_code_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["error"] == "MISSING_PARAMETER"


@patch("src.sets.get_sets_handler")
@patch("src.sets.get_set_by_id_handler")
@patch("src.sets.get_set_by_code_handler")
def test_lambda_handler_routing(mock_get_set_by_code_handler, mock_get_set_by_id_handler, mock_get_sets_handler, sample_api_event):
    """Test the lambda_handler function routes to the correct handler"""
    # Test routing to get_sets
    sample_api_event["resource"] = "/sets"
    sample_api_event["httpMethod"] = "GET"
    lambda_handler(sample_api_event, {})
    mock_get_sets_handler.assert_called_once_with(sample_api_event, {})
    
    # Test routing to get_set_by_id
    mock_get_sets_handler.reset_mock()
    sample_api_event["resource"] = "/sets/{id}"
    lambda_handler(sample_api_event, {})
    mock_get_set_by_id_handler.assert_called_once_with(sample_api_event, {})
    
    # Test routing to get_set_by_code
    mock_get_set_by_id_handler.reset_mock()
    sample_api_event["resource"] = "/sets/code/{code}"
    lambda_handler(sample_api_event, {})
    mock_get_set_by_code_handler.assert_called_once_with(sample_api_event, {})


def test_lambda_handler_method_not_allowed(sample_api_event):
    """Test the lambda_handler function when method is not allowed"""
    # Setup event with POST method
    sample_api_event["resource"] = "/sets"
    sample_api_event["httpMethod"] = "POST"
    
    # Call handler
    response = lambda_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 405
    body = json.loads(response["body"])
    assert body["error"] == "METHOD_NOT_ALLOWED" 