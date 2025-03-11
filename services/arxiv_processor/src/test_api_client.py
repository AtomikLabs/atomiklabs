#!/usr/bin/env python3
"""
Test script for the API client

This script tests the API client with the updated configuration.
"""

import logging
import os
import sys
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Import the API client
from api_client import ApiClient

def main():
    """Test the API client with the updated configuration."""
    # Set environment variables for testing
    os.environ['X_APIGW_API_ID'] = 'wgwqmoyg2a'  # API Gateway ID from the console
    
    # Create API client with the VPC endpoint URL
    vpc_endpoint_url = "https://vpce-0982aef5e74f80668-ihdqp4if.execute-api.us-west-1.vpce.amazonaws.com/dev"
    api_client = ApiClient(vpc_endpoint_url)
    
    # Log the base URL and canonical hostname
    logger.info(f"Base URL: {api_client.base_url}")
    logger.info(f"Canonical hostname: {api_client.canonical_hostname}")
    
    # Test with direct API Gateway URL
    direct_url = "https://wgwqmoyg2a.execute-api.us-west-1.amazonaws.com/dev"
    api_client_direct = ApiClient(direct_url)
    
    logger.info(f"Direct URL base URL: {api_client_direct.base_url}")
    logger.info(f"Direct URL canonical hostname: {api_client_direct.canonical_hostname}")
    
    # Test API connectivity with both clients and different endpoints
    endpoints = ['papers', 'authors', 'categories', 'sets']
    
    for endpoint in endpoints:
        try:
            logger.info(f"Testing API connectivity with direct URL to /{endpoint}...")
            response = api_client_direct._make_request('GET', endpoint, params={"limit": 1})
            logger.info(f"Direct URL response for /{endpoint}: {json.dumps(response, indent=2)}")
        except Exception as e:
            logger.error(f"Error with direct API Gateway URL to /{endpoint}: {e}")
    
    logger.info("API client test completed")

if __name__ == "__main__":
    main()
