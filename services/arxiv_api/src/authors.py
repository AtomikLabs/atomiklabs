#!/usr/bin/env python3
"""
Lambda handlers for authors API endpoints
"""
import json
import logging
import uuid
from typing import Dict, Any, Union, List

# Import the shared models and DB access layer
from shared.models.schemas import (
    Author, ErrorResponse, ValidationError, PaginatedResponse
)
from shared.db import (
    get_db_connection,
    get_author_by_id,
    search_authors,
    get_authors_by_paper
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

def get_authors_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for retrieving authors with pagination and filtering
    
    Supported query parameters:
    - page: Page number (default: 1)
    - page_size: Number of authors per page (default: 20, max: 100)
    - search: Search term for author name
    """
    try:
        logger.info("Processing get_authors request")
        
        # Parse query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        
        page = int(query_params.get('page', 1))
        page_size = min(int(query_params.get('page_size', 20)), 100)
        search_term = query_params.get('search')
        
        # Get database connection
        with get_db_connection() as db_conn:
            # Search authors
            authors, total_count = search_authors(
                db_conn,
                search_term=search_term,
                limit=page_size,
                offset=(page - 1) * page_size
            )
            
            # Calculate pagination info
            total_pages = (total_count + page_size - 1) // page_size
            
            # Build response
            response = PaginatedResponse[Author](
                items=[author.dict() for author in authors],
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                total_items=total_count
            )
            
            return _build_response(200, response.dict())
        
    except Exception as e:
        return handle_error(e)

def get_author_by_id_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for retrieving a specific author by ID
    """
    try:
        logger.info("Processing get_author_by_id request")
        
        # Get author ID from path parameters
        path_parameters = event.get('pathParameters', {}) or {}
        author_id = path_parameters.get('id')
        
        if not author_id:
            return _build_response(400, ErrorResponse(
                error_code="MISSING_PARAMETER",
                message="Author ID is required",
                details=None
            ).dict())
        
        try:
            # Validate UUID format
            author_id = str(uuid.UUID(author_id))
        except ValueError:
            return _build_response(400, ErrorResponse(
                error_code="INVALID_PARAMETER",
                message="Invalid author ID format",
                details="Author ID must be a valid UUID"
            ).dict())
        
        # Get database connection
        with get_db_connection() as db_conn:
            # Get author by ID
            author = get_author_by_id(db_conn, author_id)
            
            if not author:
                return _build_response(404, ErrorResponse(
                    error_code="NOT_FOUND",
                    message="Author not found",
                    details=f"No author found with ID {author_id}"
                ).dict())
            
            # Return the author
            return _build_response(200, author.dict())
        
    except Exception as e:
        return handle_error(e)

def get_authors_by_paper_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for retrieving authors of a specific paper
    """
    try:
        logger.info("Processing get_authors_by_paper request")
        
        # Get paper ID from path parameters
        path_parameters = event.get('pathParameters', {}) or {}
        paper_id = path_parameters.get('paper_id')
        
        if not paper_id:
            return _build_response(400, ErrorResponse(
                error_code="MISSING_PARAMETER",
                message="Paper ID is required",
                details=None
            ).dict())
        
        try:
            # Validate UUID format
            paper_id = str(uuid.UUID(paper_id))
        except ValueError:
            return _build_response(400, ErrorResponse(
                error_code="INVALID_PARAMETER",
                message="Invalid paper ID format",
                details="Paper ID must be a valid UUID"
            ).dict())
        
        # Get database connection
        with get_db_connection() as db_conn:
            # Get authors by paper ID
            authors = get_authors_by_paper(db_conn, paper_id)
            
            # Build response
            response = PaginatedResponse[Author](
                items=[author.dict() for author in authors],
                page=1,
                page_size=len(authors),
                total_pages=1,
                total_items=len(authors)
            )
            
            return _build_response(200, response.dict())
        
    except Exception as e:
        return handle_error(e)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler that routes to specific handlers based on the HTTP method and path
    """
    try:
        logger.info(f"Processing authors API request: {json.dumps(event)}")
        
        http_method = event.get('httpMethod', '')
        resource = event.get('resource', '')
        
        # Route to the appropriate handler based on the HTTP method and resource
        if http_method == 'GET' and resource == '/authors':
            return get_authors_handler(event, context)
        elif http_method == 'GET' and resource == '/authors/{id}':
            return get_author_by_id_handler(event, context)
        elif http_method == 'GET' and resource == '/papers/{paper_id}/authors':
            return get_authors_by_paper_handler(event, context)
        else:
            return _build_response(405, ErrorResponse(
                error_code="METHOD_NOT_ALLOWED",
                message=f"Method {http_method} not allowed for resource {resource}",
                details=None
            ).dict())
            
    except Exception as e:
        return handle_error(e) 