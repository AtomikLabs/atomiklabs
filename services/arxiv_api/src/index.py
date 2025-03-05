#!/usr/bin/env python3
"""
Main Lambda handler for arXiv Data Layer API
Routes requests to the appropriate endpoint handlers
"""
import json
import logging
from typing import Dict, Any

# Import endpoint handlers
from papers import lambda_handler as papers_handler
from authors import lambda_handler as authors_handler
from categories import lambda_handler as categories_handler
from sets import lambda_handler as sets_handler
from abstracts import lambda_handler as abstracts_handler

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler that routes requests to the appropriate endpoint handlers
    """
    try:
        logger.info(f"Received API Gateway event: {json.dumps(event)}")
        
        resource = event.get('resource', '')
        
        # Route to the appropriate handler based on the resource path
        if resource.startswith('/papers'):
            # Check if this is an abstract operation
            if '/abstract' in resource:
                return abstracts_handler(event, context)
            return papers_handler(event, context)
        elif resource.startswith('/authors'):
            return authors_handler(event, context)
        elif resource.startswith('/categories'):
            return categories_handler(event, context)
        elif resource.startswith('/sets'):
            return sets_handler(event, context)
        else:
            # Handle unknown resources
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error_code': 'NOT_FOUND',
                    'message': f'Resource not found: {resource}',
                    'details': None
                })
            }
            
    except Exception as e:
        logger.exception("Error processing request")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error_code': 'SERVER_ERROR',
                'message': 'An unexpected error occurred',
                'details': str(e)
            })
        } 