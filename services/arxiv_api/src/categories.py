#!/usr/bin/env python3
"""
Lambda handlers for categories API endpoints
"""
import json
import logging
from typing import Dict, Any, Union, List

# Import the shared models and DB access layer
from shared.models.schemas import (
    Category, ErrorResponse, ValidationError, PaginatedResponse
)
from shared.db import (
    get_db_connection,
    get_all_categories,
    get_category_by_code
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def _build_response(
    status_code: int, 
    body: Union[Dict[str, Any], List[Dict[str, Any]], str]
) -> Dict[str, Any]:
    """
    Helper function to build an API Gateway response
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,GET'
        },
        'body': json.dumps(body) if isinstance(body, (dict, list)) else body
    }

def handle_error(error: Exception) -> Dict[str, Any]:
    """
    Handle exceptions and return appropriate error responses
    """
    logger.exception("Error processing request")
    
    if isinstance(error, ValidationError):
        return _build_response(400, ErrorResponse(
            error_code="VALIDATION_ERROR",
            message=str(error),
            details=error.errors
        ).dict())
    
    # Handle database connection errors
    if "database" in str(error).lower() or "connection" in str(error).lower():
        return _build_response(503, ErrorResponse(
            error_code="DATABASE_ERROR",
            message="Database connection error",
            details=str(error)
        ).dict())
    
    # Generic error handling
    return _build_response(500, ErrorResponse(
        error_code="SERVER_ERROR",
        message="An unexpected error occurred",
        details=str(error)
    ).dict())

def get_categories_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for retrieving all categories
    """
    try:
        logger.info("Processing get_categories request")
        
        # Get database connection
        with get_db_connection() as db_conn:
            # Get all categories
            categories = get_all_categories(db_conn)
            
            # Build response
            response = PaginatedResponse[Category](
                items=[category.dict() for category in categories],
                page=1,
                page_size=len(categories),
                total_pages=1,
                total_items=len(categories)
            )
            
            return _build_response(200, response.dict())
        
    except Exception as e:
        return handle_error(e)

def get_category_by_code_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for retrieving a specific category by code
    """
    try:
        logger.info("Processing get_category_by_code request")
        
        # Get category code from path parameters
        path_parameters = event.get('pathParameters', {}) or {}
        category_code = path_parameters.get('code')
        
        if not category_code:
            return _build_response(400, ErrorResponse(
                error_code="MISSING_PARAMETER",
                message="Category code is required",
                details=None
            ).dict())
        
        # Get database connection
        with get_db_connection() as db_conn:
            # Get category by code
            category = get_category_by_code(db_conn, category_code)
            
            if not category:
                return _build_response(404, ErrorResponse(
                    error_code="NOT_FOUND",
                    message="Category not found",
                    details=f"No category found with code {category_code}"
                ).dict())
            
            # Return the category
            return _build_response(200, category.dict())
        
    except Exception as e:
        return handle_error(e)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler that routes to specific handlers based on the HTTP method and path
    """
    try:
        logger.info(f"Processing categories API request: {json.dumps(event)}")
        
        http_method = event.get('httpMethod', '')
        resource = event.get('resource', '')
        
        # Route to the appropriate handler based on the HTTP method and resource
        if http_method == 'GET' and resource == '/categories':
            return get_categories_handler(event, context)
        elif http_method == 'GET' and resource == '/categories/{code}':
            return get_category_by_code_handler(event, context)
        else:
            return _build_response(405, ErrorResponse(
                error_code="METHOD_NOT_ALLOWED",
                message=f"Method {http_method} not allowed for resource {resource}",
                details=None
            ).dict())
            
    except Exception as e:
        return handle_error(e) 