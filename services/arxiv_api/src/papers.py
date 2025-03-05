#!/usr/bin/env python3
"""
Lambda handlers for papers API endpoints
"""
import json
import logging
import uuid
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

# Import the shared models and DB access layer
from shared.models.schemas import (
    Paper, PaperDetail, PaperSearchRequest, PaginatedResponse,
    ErrorResponse, ValidationError, APIResponse
)
from shared.db import (
    get_db_connection,
    get_paper_by_id,
    search_papers,
    get_papers_by_category,
    get_papers_by_date_range
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
            'Access-Control-Allow-Methods': 'OPTIONS,GET,POST'
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

def get_papers_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for retrieving papers with pagination and filtering
    
    Supported query parameters:
    - page: Page number (default: 1)
    - page_size: Number of papers per page (default: 20, max: 100)
    - category: Filter by category code
    - date_from: Filter by publication date (ISO format)
    - date_to: Filter by publication date (ISO format)
    - search: Search term for paper title and abstract
    """
    try:
        logger.info("Processing get_papers request")
        
        # Parse query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        
        # Create search request from query parameters
        search_request = PaperSearchRequest(
            page=int(query_params.get('page', 1)),
            page_size=min(int(query_params.get('page_size', 20)), 100),
            category=query_params.get('category'),
            date_from=datetime.fromisoformat(query_params['date_from']) if 'date_from' in query_params else None,
            date_to=datetime.fromisoformat(query_params['date_to']) if 'date_to' in query_params else None,
            search_term=query_params.get('search')
        )
        
        logger.info(f"Search request: {search_request.dict()}")
        
        # Get database connection
        with get_db_connection() as db_conn:
            if search_request.search_term:
                # Search papers by term
                papers, total_count = search_papers(
                    db_conn,
                    search_term=search_request.search_term,
                    category=search_request.category,
                    date_from=search_request.date_from,
                    date_to=search_request.date_to,
                    limit=search_request.page_size,
                    offset=(search_request.page - 1) * search_request.page_size
                )
            elif search_request.category:
                # Get papers by category
                papers, total_count = get_papers_by_category(
                    db_conn,
                    category=search_request.category,
                    date_from=search_request.date_from,
                    date_to=search_request.date_to,
                    limit=search_request.page_size,
                    offset=(search_request.page - 1) * search_request.page_size
                )
            elif search_request.date_from or search_request.date_to:
                # Get papers by date range
                papers, total_count = get_papers_by_date_range(
                    db_conn,
                    date_from=search_request.date_from,
                    date_to=search_request.date_to,
                    limit=search_request.page_size,
                    offset=(search_request.page - 1) * search_request.page_size
                )
            else:
                # Get all papers with pagination
                papers, total_count = search_papers(
                    db_conn,
                    limit=search_request.page_size,
                    offset=(search_request.page - 1) * search_request.page_size
                )
        
        # Calculate pagination info
        total_pages = (total_count + search_request.page_size - 1) // search_request.page_size
        
        # Build response
        response = PaginatedResponse[Paper](
            items=[paper.dict() for paper in papers],
            page=search_request.page,
            page_size=search_request.page_size,
            total_pages=total_pages,
            total_items=total_count
        )
        
        return _build_response(200, response.dict())
        
    except Exception as e:
        return handle_error(e)

def get_paper_by_id_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for retrieving a specific paper by ID
    """
    try:
        logger.info("Processing get_paper_by_id request")
        
        # Get paper ID from path parameters
        path_parameters = event.get('pathParameters', {}) or {}
        paper_id = path_parameters.get('id')
        
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
            # Get paper by ID
            paper = get_paper_by_id(db_conn, paper_id)
            
            if not paper:
                return _build_response(404, ErrorResponse(
                    error_code="NOT_FOUND",
                    message="Paper not found",
                    details=f"No paper found with ID {paper_id}"
                ).dict())
            
            # Build detailed paper response with authors and categories
            response = PaperDetail.from_orm(paper)
            
            return _build_response(200, response.dict())
        
    except Exception as e:
        return handle_error(e)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler that routes to specific handlers based on the HTTP method and path
    """
    try:
        logger.info(f"Processing papers API request: {json.dumps(event)}")
        
        http_method = event.get('httpMethod', '')
        resource = event.get('resource', '')
        
        # Route to the appropriate handler based on the HTTP method and resource
        if http_method == 'GET' and resource == '/papers':
            return get_papers_handler(event, context)
        elif http_method == 'GET' and resource == '/papers/{id}':
            return get_paper_by_id_handler(event, context)
        else:
            return _build_response(405, ErrorResponse(
                error_code="METHOD_NOT_ALLOWED",
                message=f"Method {http_method} not allowed for resource {resource}",
                details=None
            ).dict())
            
    except Exception as e:
        return handle_error(e) 