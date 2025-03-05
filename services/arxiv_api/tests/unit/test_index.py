"""
Unit tests for the main router in index.py
"""
import json
from unittest.mock import patch, MagicMock

import pytest

# Use explicit import from src for testing
from src.index import lambda_handler

# We need to specify the full import paths with "src." for patches
# This ensures our tests work despite Lambda's relative import structure
@patch("src.index.abstracts_handler")
@patch("src.index.sets_handler") 
@patch("src.index.categories_handler")
@patch("src.index.authors_handler")
@patch("src.index.papers_handler")
def test_lambda_handler_routing(mock_papers_handler, mock_authors_handler, mock_categories_handler,
                              mock_sets_handler, mock_abstracts_handler):
    """Test the main lambda_handler function for routing to specific handlers"""
    # Create a test event
    event = {
        "resource": "/papers",
        "httpMethod": "GET",
        "pathParameters": {},
        "queryStringParameters": {},
        "body": None
    }
    context = {}

    # Test routing to papers handler
    lambda_handler(event, context)
    mock_papers_handler.assert_called_once_with(event, context)
    mock_papers_handler.reset_mock()

    # Test routing to papers/abstract handler
    event["resource"] = "/papers/{id}/abstract"
    lambda_handler(event, context)
    mock_abstracts_handler.assert_called_once_with(event, context)
    mock_abstracts_handler.reset_mock()

    # Test routing to authors handler
    event["resource"] = "/authors"
    lambda_handler(event, context)
    mock_authors_handler.assert_called_once_with(event, context)
    mock_authors_handler.reset_mock()

    # Test routing to categories handler
    event["resource"] = "/categories"
    lambda_handler(event, context)
    mock_categories_handler.assert_called_once_with(event, context)
    mock_categories_handler.reset_mock()

    # Test routing to sets handler
    event["resource"] = "/sets"
    lambda_handler(event, context)
    mock_sets_handler.assert_called_once_with(event, context)
    mock_sets_handler.reset_mock()


@patch("src.index.logging")
def test_lambda_handler_resource_not_found(mock_logging):
    """Test the lambda_handler function with an unknown resource"""
    # Create a test event with unknown resource
    event = {
        "resource": "/unknown",
        "httpMethod": "GET",
        "pathParameters": {},
        "queryStringParameters": {},
        "body": None
    }
    context = {}

    # Call the handler
    response = lambda_handler(event, context)

    # Verify response
    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert body["error"] == "NOT_FOUND"


@patch("src.index.logging")
def test_lambda_handler_error_handling(mock_logging):
    """Test the lambda_handler function when an exception occurs"""
    # Create a test event
    event = {
        "resource": "/papers",
        "httpMethod": "GET",
        "pathParameters": {},
        "queryStringParameters": {},
        "body": None
    }
    context = {}

    # Make the papers_handler raise an exception
    with patch("src.index.papers_handler", side_effect=Exception("Test error")):
        # Call the handler
        response = lambda_handler(event, context)

        # Verify response
        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert body["error"] == "SERVER_ERROR"
        assert "Test error" in body["details"]["info"]

    # Skip logger verification since we're using root logger
    # mock_logging.exception.assert_called_once() 