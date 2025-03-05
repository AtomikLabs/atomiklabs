#!/usr/bin/env python3
"""
Lambda handlers for managing paper abstracts in S3
Provides endpoints for retrieving, storing, and deleting paper abstracts
"""
import json
import logging
import uuid
import os
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Union, List, Optional

# Import the shared models and DB access layer
from shared.models.schemas import (
    Paper, ErrorResponse, ValidationError
)
from shared.db import (
    get_db_connection,
    get_paper_by_id
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get S3 bucket name from environment variable or SSM Parameter Store
import boto3
from botocore.exceptions import ClientError

def get_s3_bucket_name() -> str:
    """
    Get the S3 bucket name from SSM Parameter Store
    """
    try:
        ssm = boto3.client('ssm')
        response = ssm.get_parameter(
            Name=os.environ.get('CONFIG_PATH') + '/s3_bucket',
            WithDecryption=False
        )
        return response['Parameter']['Value']
    except ClientError as e:
        logger.error(f"Error retrieving S3 bucket name from SSM: {e}")
        # If SSM parameter access fails, raise an error
        # This ensures the Lambda will fail explicitly rather than using a default
        raise RuntimeError("Failed to retrieve S3 bucket name from SSM Parameter Store")

# Initialize S3 client
s3_client = boto3.client('s3')
s3_bucket = get_s3_bucket_name()

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
            'Access-Control-Allow-Methods': 'OPTIONS,GET,PUT,DELETE'
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
    
    # Handle S3 access errors
    if isinstance(error, ClientError):
        error_code = error.response.get('Error', {}).get('Code', 'UnknownS3Error')
        status_code = 503  # Default to service unavailable
        
        if error_code == 'NoSuchKey':
            status_code = 404
            message = "Abstract not found"
        elif error_code == 'AccessDenied':
            status_code = 403
            message = "Access denied to abstract storage"
        else:
            message = f"S3 error: {error_code}"
            
        return _build_response(status_code, ErrorResponse(
            error_code="S3_ERROR",
            message=message,
            details=str(error)
        ).dict())
    
    # Generic error handling
    return _build_response(500, ErrorResponse(
        error_code="SERVER_ERROR",
        message="An unexpected error occurred",
        details=str(error)
    ).dict())

def get_abstract_s3_key(paper_id: str, arxiv_identifier: str, set_code: str) -> str:
    """
    Generate the S3 key for a paper abstract based on arXiv identifier and set code
    Format: abstracts/{set_code}/{YYYY}/{MM}/{arxiv_identifier}.txt
    """
    # Extract year and month from arXiv identifier (format: YYMM.NNNNN)
    # If not a standard format, use a default organization
    try:
        if '.' in arxiv_identifier:
            year_month = arxiv_identifier.split('.')[0]
            if len(year_month) == 4:  # Standard format YYMM
                year = f"20{year_month[:2]}"  # Convert YY to 20YY
                month = year_month[2:4]
                return f"abstracts/{set_code}/{year}/{month}/{arxiv_identifier}.txt"
    except Exception as e:
        logger.warning(f"Error parsing arXiv identifier {arxiv_identifier}: {e}")
    
    # Fallback to a simple organization by paper_id if parsing fails
    return f"abstracts/{set_code}/other/{paper_id}.txt"

def get_abstract_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for retrieving a paper abstract from S3
    """
    try:
        logger.info("Processing get_abstract request")
        
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
        
        # Get database connection to retrieve paper details
        with get_db_connection() as db_conn:
            # Get paper by ID
            paper = get_paper_by_id(db_conn, paper_id)
            
            if not paper:
                return _build_response(404, ErrorResponse(
                    error_code="NOT_FOUND",
                    message="Paper not found",
                    details=f"No paper found with ID {paper_id}"
                ).dict())
            
            # Generate S3 key based on paper details
            s3_key = get_abstract_s3_key(
                paper_id=paper_id, 
                arxiv_identifier=paper.arxiv_identifier,
                set_code=paper.primary_category
            )
            
            try:
                # Retrieve abstract from S3
                response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
                abstract_content = response['Body'].read().decode('utf-8')
                
                # Return the abstract
                return _build_response(200, {
                    "paper_id": paper_id,
                    "arxiv_identifier": paper.arxiv_identifier,
                    "abstract": abstract_content
                })
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code')
                if error_code == 'NoSuchKey':
                    return _build_response(404, ErrorResponse(
                        error_code="ABSTRACT_NOT_FOUND",
                        message="Abstract not found in storage",
                        details=f"No abstract found for paper ID {paper_id}"
                    ).dict())
                else:
                    raise
        
    except Exception as e:
        return handle_error(e)

def store_abstract_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for storing a paper abstract in S3
    """
    try:
        logger.info("Processing store_abstract request")
        
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
        
        # Parse request body
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            return _build_response(400, ErrorResponse(
                error_code="INVALID_REQUEST",
                message="Invalid JSON in request body",
                details=None
            ).dict())
        
        abstract_content = body.get('abstract')
        if not abstract_content:
            return _build_response(400, ErrorResponse(
                error_code="MISSING_CONTENT",
                message="Abstract content is required",
                details=None
            ).dict())
        
        # Get database connection to retrieve paper details
        with get_db_connection() as db_conn:
            # Get paper by ID
            paper = get_paper_by_id(db_conn, paper_id)
            
            if not paper:
                return _build_response(404, ErrorResponse(
                    error_code="NOT_FOUND",
                    message="Paper not found",
                    details=f"No paper found with ID {paper_id}"
                ).dict())
            
            # Generate S3 key based on paper details
            s3_key = get_abstract_s3_key(
                paper_id=paper_id, 
                arxiv_identifier=paper.arxiv_identifier,
                set_code=paper.primary_category
            )
            
            # Store abstract in S3
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=s3_key,
                Body=abstract_content.encode('utf-8'),
                ContentType='text/plain'
            )
            
            logger.info(f"Successfully stored abstract for paper {paper_id} at {s3_key}")
            
            # Return success response
            return _build_response(200, {
                "paper_id": paper_id,
                "arxiv_identifier": paper.arxiv_identifier,
                "message": "Abstract stored successfully",
                "s3_key": s3_key
            })
        
    except Exception as e:
        return handle_error(e)

def delete_abstract_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for deleting a paper abstract from S3
    """
    try:
        logger.info("Processing delete_abstract request")
        
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
        
        # Get database connection to retrieve paper details
        with get_db_connection() as db_conn:
            # Get paper by ID
            paper = get_paper_by_id(db_conn, paper_id)
            
            if not paper:
                return _build_response(404, ErrorResponse(
                    error_code="NOT_FOUND",
                    message="Paper not found",
                    details=f"No paper found with ID {paper_id}"
                ).dict())
            
            # Generate S3 key based on paper details
            s3_key = get_abstract_s3_key(
                paper_id=paper_id, 
                arxiv_identifier=paper.arxiv_identifier,
                set_code=paper.primary_category
            )
            
            try:
                # Check if the object exists before deleting
                s3_client.head_object(Bucket=s3_bucket, Key=s3_key)
                
                # Delete abstract from S3
                s3_client.delete_object(Bucket=s3_bucket, Key=s3_key)
                
                logger.info(f"Successfully deleted abstract for paper {paper_id} at {s3_key}")
                
                # Return success response
                return _build_response(200, {
                    "paper_id": paper_id,
                    "arxiv_identifier": paper.arxiv_identifier,
                    "message": "Abstract deleted successfully"
                })
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code')
                if error_code == 'NoSuchKey' or error_code == '404':
                    return _build_response(404, ErrorResponse(
                        error_code="ABSTRACT_NOT_FOUND",
                        message="Abstract not found in storage",
                        details=f"No abstract found for paper ID {paper_id}"
                    ).dict())
                else:
                    raise
        
    except Exception as e:
        return handle_error(e)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler that routes to specific handlers based on the HTTP method and path
    """
    try:
        logger.info(f"Processing abstracts API request: {json.dumps(event)}")
        
        http_method = event.get('httpMethod', '')
        resource = event.get('resource', '')
        
        # Route to the appropriate handler based on the HTTP method and resource
        if http_method == 'GET' and resource == '/papers/{id}/abstract':
            return get_abstract_handler(event, context)
        elif http_method == 'PUT' and resource == '/papers/{id}/abstract':
            return store_abstract_handler(event, context)
        elif http_method == 'DELETE' and resource == '/papers/{id}/abstract':
            return delete_abstract_handler(event, context)
        else:
            return _build_response(405, ErrorResponse(
                error_code="METHOD_NOT_ALLOWED",
                message=f"Method {http_method} not allowed for resource {resource}",
                details=None
            ).dict())
            
    except Exception as e:
        return handle_error(e) 