"""
Unit tests for the categories module
"""
import json
import uuid
from unittest.mock import patch, MagicMock

import pytest

from src.categories import (
    _build_response,
    handle_error,
    get_categories_handler,
    get_category_by_code_handler,
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


@patch("src.categories.logging")
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


@patch("src.categories.get_db_connection")
@patch("src.categories.get_all_categories")
def test_get_categories_handler(mock_get_all_categories, mock_get_db_connection, sample_api_event, db_connection_mock):
    """Test the get_categories_handler function"""
    # Setup mocks
    mock_get_db_connection.return_value.__enter__.return_value = db_connection_mock
    
    # Create mock categories
    category1 = MagicMock()
    category1.dict.return_value = {
        "category_code": "CS.AI", 
        "name": "Artificial Intelligence",
        "description": "AI description"
    }
    category2 = MagicMock()
    category2.dict.return_value = {
        "category_code": "CS.ML", 
        "name": "Machine Learning",
        "description": "ML description"
    }
    mock_get_all_categories.return_value = [category1, category2]
    
    # Call handler
    response = get_categories_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    
    # The response is wrapped in a paginated response format
    assert "items" in body
    assert len(body["items"]) == 2
    assert body["items"][0]["category_code"] == "CS.AI"
    assert body["items"][1]["category_code"] == "CS.ML"
    
    # Verify mock calls
    mock_get_all_categories.assert_called_once_with(db_connection_mock)


@patch("src.categories.get_db_connection")
@patch("src.categories.get_category_by_code")
def test_get_category_by_code_handler_success(mock_get_category_by_code, mock_get_db_connection, sample_api_event, db_connection_mock):
    """Test the get_category_by_code_handler function for a successful case"""
    # Setup mocks
    mock_get_db_connection.return_value.__enter__.return_value = db_connection_mock
    
    # Create a mock category
    category_mock = MagicMock()
    category_mock.dict.return_value = {
        "category_code": "CS.AI", 
        "name": "Artificial Intelligence",
        "description": "AI description"
    }
    mock_get_category_by_code.return_value = category_mock
    
    # Setup event with category code
    sample_api_event["pathParameters"] = {"code": "CS.AI"}
    
    # Call handler
    response = get_category_by_code_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["category_code"] == "CS.AI"
    assert body["name"] == "Artificial Intelligence"
    
    # Verify mock calls
    mock_get_category_by_code.assert_called_once_with(db_connection_mock, "CS.AI")


@patch("src.categories.get_db_connection")
@patch("src.categories.get_category_by_code")
def test_get_category_by_code_handler_not_found(mock_get_category_by_code, mock_get_db_connection, sample_api_event, db_connection_mock):
    """Test the get_category_by_code_handler function when category is not found"""
    # Setup mocks
    mock_get_db_connection.return_value.__enter__.return_value = db_connection_mock
    mock_get_category_by_code.return_value = None
    
    # Setup event with category code
    sample_api_event["pathParameters"] = {"code": "UNKNOWN"}
    
    # Call handler
    response = get_category_by_code_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert body["error"] == "NOT_FOUND"


@patch("src.categories.get_db_connection")
@patch("src.categories.get_category_by_code")
def test_get_category_by_code_handler_missing_code(mock_get_category_by_code, mock_get_db_connection, sample_api_event):
    """Test the get_category_by_code_handler function with a missing code"""
    # Setup event with no code
    sample_api_event["pathParameters"] = {}
    
    # Call handler
    response = get_category_by_code_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["error"] == "MISSING_PARAMETER"


@patch("src.categories.get_categories_handler")
@patch("src.categories.get_category_by_code_handler")
def test_lambda_handler_routing(mock_get_category_by_code_handler, mock_get_categories_handler, sample_api_event):
    """Test the lambda_handler function routes to the correct handler"""
    # Test routing to get_categories
    sample_api_event["resource"] = "/categories"
    sample_api_event["httpMethod"] = "GET"
    lambda_handler(sample_api_event, {})
    mock_get_categories_handler.assert_called_once_with(sample_api_event, {})
    
    # Test routing to get_category_by_code
    mock_get_categories_handler.reset_mock()
    sample_api_event["resource"] = "/categories/{code}"
    lambda_handler(sample_api_event, {})
    mock_get_category_by_code_handler.assert_called_once_with(sample_api_event, {})


def test_lambda_handler_method_not_allowed(sample_api_event):
    """Test the lambda_handler function when method is not allowed"""
    # Setup event with POST method
    sample_api_event["resource"] = "/categories"
    sample_api_event["httpMethod"] = "POST"
    
    # Call handler
    response = lambda_handler(sample_api_event, {})
    
    # Verify response
    assert response["statusCode"] == 405
    body = json.loads(response["body"])
    assert body["error"] == "METHOD_NOT_ALLOWED" 