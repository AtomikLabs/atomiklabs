#!/usr/bin/env python3
"""
Lambda handlers for arXiv sets API endpoints
"""
import json
import logging
import uuid
from typing import Dict, Any, Union, List

# Import the shared models and DB access layer
from shared.models.schemas import (
    ArxivSet, ErrorResponse, ValidationError, PaginatedResponse
)
from shared.db import (
    get_db_connection,
    get_all_sets,
    get_set_by_code,
    get_set_by_id
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

def get_sets_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for retrieving all arXiv sets
    """
    try:
        logger.info("Processing get_sets request")
        
        # Get database connection
        with get_db_connection() as db_conn:
            # Get all sets
            sets = get_all_sets(db_conn)
            
            # Build response
            response = PaginatedResponse[ArxivSet](
                items=[arxiv_set.dict() for arxiv_set in sets],
                page=1,
                page_size=len(sets),
                total_pages=1,
                total_items=len(sets)
            )
            
            return _build_response(200, response.dict())
        
    except Exception as e:
        return handle_error(e)

def get_set_by_id_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for retrieving a specific arXiv set by ID
    """
    try:
        logger.info("Processing get_set_by_id request")
        
        # Get set ID from path parameters
        path_parameters = event.get('pathParameters', {}) or {}
        set_id = path_parameters.get('id')
        
        if not set_id:
            return _build_response(400, ErrorResponse(
                error_code="MISSING_PARAMETER",
                message="Set ID is required",
                details=None
            ).dict())
        
        try:
            # Validate UUID format
            set_id = str(uuid.UUID(set_id))
        except ValueError:
            return _build_response(400, ErrorResponse(
                error_code="INVALID_PARAMETER",
                message="Invalid set ID format",
                details="Set ID must be a valid UUID"
            ).dict())
        
        # Get database connection
        with get_db_connection() as db_conn:
            # Get set by ID
            arxiv_set = get_set_by_id(db_conn, set_id)
            
            if not arxiv_set:
                return _build_response(404, ErrorResponse(
                    error_code="NOT_FOUND",
                    message="Set not found",
                    details=f"No set found with ID {set_id}"
                ).dict())
            
            # Return the set
            return _build_response(200, arxiv_set.dict())
        
    except Exception as e:
        return handle_error(e)

def get_set_by_code_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for retrieving a specific arXiv set by code
    """
    try:
        logger.info("Processing get_set_by_code request")
        
        # Get set code from path parameters
        path_parameters = event.get('pathParameters', {}) or {}
        set_code = path_parameters.get('code')
        
        if not set_code:
            return _build_response(400, ErrorResponse(
                error_code="MISSING_PARAMETER",
                message="Set code is required",
                details=None
            ).dict())
        
        # Get database connection
        with get_db_connection() as db_conn:
            # Get set by code
            arxiv_set = get_set_by_code(db_conn, set_code)
            
            if not arxiv_set:
                return _build_response(404, ErrorResponse(
                    error_code="NOT_FOUND",
                    message="Set not found",
                    details=f"No set found with code {set_code}"
                ).dict())
            
            # Return the set
            return _build_response(200, arxiv_set.dict())
        
    except Exception as e:
        return handle_error(e)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler that routes to specific handlers based on the HTTP method and path
    """
    try:
        logger.info(f"Processing sets API request: {json.dumps(event)}")
        
        http_method = event.get('httpMethod', '')
        resource = event.get('resource', '')
        
        # Route to the appropriate handler based on the HTTP method and resource
        if http_method == 'GET' and resource == '/sets':
            return get_sets_handler(event, context)
        elif http_method == 'GET' and resource == '/sets/{id}':
            return get_set_by_id_handler(event, context)
        elif http_method == 'GET' and resource == '/sets/code/{code}':
            return get_set_by_code_handler(event, context)
        else:
            return _build_response(405, ErrorResponse(
                error_code="METHOD_NOT_ALLOWED",
                message=f"Method {http_method} not allowed for resource {resource}",
                details=None
            ).dict())
            
    except Exception as e:
        return handle_error(e) 