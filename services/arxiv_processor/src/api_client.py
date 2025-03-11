#!/usr/bin/env python3
"""
API client for interacting with the ArXiv API Gateway
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional, Union
import uuid
import datetime
import os
from urllib.parse import urlparse, urlencode
from datetime import datetime

import requests
from requests.exceptions import RequestException

# Add boto3 imports for authentication
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

logger = logging.getLogger(__name__)


class CircuitBreakerOpenError(Exception):
    """Exception raised when the circuit breaker is open."""
    pass


class ApiClient:
    """Client for interacting with the ArXiv API Gateway."""
    
    def __init__(self, base_url: str, max_retries: int = 3, retry_delay: int = 1):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL for the API Gateway
            max_retries: Maximum number of retries for API calls
            retry_delay: Initial delay between retries (with exponential backoff)
        """
        self.base_url = base_url.rstrip('/')
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Set up AWS credentials for API Gateway authentication
        # Use the default credential provider chain - much simpler!
        self.session = boto3.Session()
        self.credentials = self.session.get_credentials()
        self.region = self.session.region_name or os.environ.get('AWS_REGION', 'us-west-1')
        
        # Get API Gateway ID from environment variable
        self.api_gateway_id = os.environ.get('X_APIGW_API_ID')
        
        # Check if this is an HTTP API or a REST API
        self.api_type = os.environ.get('API_TYPE', 'REST')
        
        # Extract the environment/stage from the base URL
        # The base URL format is: https://vpce-xxx.execute-api.region.vpce.amazonaws.com/stage
        url_parts = self.base_url.split('/')
        self.environment = url_parts[-1] if len(url_parts) > 3 else 'dev'
        
        logger.info(f"API Client initialized for {self.api_type} API with ID {self.api_gateway_id}")
        logger.info(f"Using environment/stage: {self.environment}")
        logger.info(f"Base URL: {self.base_url}")
        
        # Construct the canonical hostname for API Gateway (for SigV4 signing)
        if self.api_gateway_id:
            # The canonical URL should be: https://api-id.execute-api.region.amazonaws.com/stage
            self.canonical_hostname = f"https://{self.api_gateway_id}.execute-api.{self.region}.amazonaws.com"
            logger.info(f"Using canonical hostname for SigV4 signing: {self.canonical_hostname}")
        else:
            # Fall back to using the VPC endpoint URL without the stage
            base_without_stage = '/'.join(url_parts[:-1]) if len(url_parts) > 3 else self.base_url
            self.canonical_hostname = base_without_stage
            logger.warning(f"X_APIGW_API_ID not found in environment variables. Using VPC endpoint URL for signing: {self.canonical_hostname}")
        
        # Log credential information (safely)
        if self.credentials:
            cred_type = self.credentials.__class__.__name__
            frozen_creds = self.credentials.get_frozen_credentials()
            access_key_preview = "..." + frozen_creds.access_key[-4:] if frozen_creds.access_key else "None"
            logger.info(f"AWS credentials initialized for region {self.region} (Type: {cred_type}, Key: {access_key_preview})")
            logger.info(f"Security token present: {bool(frozen_creds.token)}")
            
            # Verify credentials are valid
            if not frozen_creds.access_key:
                logger.error("Credentials found but access key is empty")
        else:
            logger.warning("No AWS credentials found for API Gateway authentication")
        
        # Circuit breaker state
        self._failures = 0
        self._failure_threshold = 5
        self._circuit_open = False
        self._last_failure_time = 0
        self._circuit_reset_timeout = 30  # 30 seconds for recovery
        self._half_open_success = 0
        self._half_open_required_successes = 3  # Require 3 successful requests to close the circuit
    
    def _check_circuit(self):
        """Check if circuit breaker is open and handle reset logic"""
        if not self._circuit_open:
            return True
            
        # Check if enough time has passed to try again
        current_time = time.time()
        if current_time - self._last_failure_time >= self._circuit_reset_timeout:
            logger.info("Circuit breaker reset timeout reached, transitioning to half-open state")
            # Don't fully close the circuit yet, just allow one request through
            # We'll close it completely after a few successful requests
            return True
            
        logger.warning(f"Circuit breaker is open. API Gateway appears to be down. Will retry in {self._circuit_reset_timeout - (current_time - self._last_failure_time):.0f} seconds")
        return False
    
    def _handle_success(self):
        """Handle a successful API call"""
        if self._circuit_open:
            # We're in a half-open state, track successful calls
            self._half_open_success += 1
            if self._half_open_success >= self._half_open_required_successes:
                logger.info(f"Circuit breaker closing after {self._half_open_success} successful requests")
                self._circuit_open = False
                self._failures = 0
                self._half_open_success = 0
        else:
            # Normal operation, reset failure counter
            self._failures = 0
    
    def _handle_failure(self, status_code=None):
        """Handle a failed API call"""
        self._failures += 1
        self._last_failure_time = time.time()
        self._half_open_success = 0  # Reset success counter on any failure
        
        # Open the circuit after threshold failures
        if self._failures >= self._failure_threshold:
            logger.error(f"Circuit breaker threshold reached ({self._failures} failures). Opening circuit breaker.")
            self._circuit_open = True
            
        # Log different messages based on status code
        if status_code:
            if 500 <= status_code < 600:
                logger.error(f"Server error (HTTP {status_code}) - This could indicate an issue with the API Lambda function")
            elif status_code == 429:
                logger.warning(f"Rate limited (HTTP 429) - Too many requests, backing off")
            elif 400 <= status_code < 500:
                logger.warning(f"Client error (HTTP {status_code}) - Check the API request format")
                
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the API Gateway with retry logic.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            data: Request data (for POST, PUT)
            params: Query parameters (for GET)
            
        Returns:
            Response data as a dictionary
            
        Raises:
            RequestException: If the request fails after retries
            CircuitBreakerOpenError: If the circuit breaker is open
        """
        # Check if circuit breaker is open
        if not self._check_circuit():
            raise CircuitBreakerOpenError("Circuit breaker is open, API is not responsive")

        # Build the base URL
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Build query string if we have params
        query_string = ''
        if params:
            query_string = urlencode(params)
            
        # Complete URL including query string
        full_url = url
        if query_string:
            full_url = f"{url}?{query_string}"
            
        # Handle JSON serialization for request body
        request_body = None
        if data and method.upper() in ['POST', 'PUT']:
            data = self._serialize_json_safe(data)
            request_body = json.dumps(data)
        
        retry_count = 0
        current_delay = self.retry_delay
        
        while retry_count <= self.max_retries:
            try:
                # Extract host from URL for the Host header
                parsed_url = urlparse(url)
                host = parsed_url.netloc
                
                # Basic headers required for all requests
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "ArxivProcessor/1.0",
                    "Host": host,  # Required for SigV4
                    "X-Amz-Date": datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')  # Required for SigV4
                }
                
                # No SigV4 signing - API Gateway no longer requires authentication
                logger.debug(f"Making request without SigV4 signing: {method} {full_url}")
                logger.debug(f"Headers: {headers}")
                
                # Make the request directly to the VPC endpoint URL
                response = requests.request(
                    method=method,
                    url=full_url,
                    headers=headers,
                    data=request_body,
                    timeout=10
                )
                
                # Handle the response
                if response.status_code < 400:
                    # Success - handle circuit breaker state
                    self._handle_success()
                    
                    # Parse JSON response
                    try:
                        return response.json()
                    except ValueError:
                        if response.text.strip():
                            logger.warning(f"Response is not valid JSON: {response.text[:100]}")
                        return {"message": response.text or "Empty response"}
                else:
                    # Log detailed error information
                    log_prefix = f"Request failed: {method} {full_url}"
                    logger.warning(f"{log_prefix} - Status: {response.status_code}")
                    
                    try:
                        error_body = response.json()
                        logger.warning(f"Response body: {error_body}")
                    except:
                        logger.warning(f"Response text: {response.text[:200]}")
                    
                    # Handle specific error cases
                    if response.status_code == 403:
                        logger.error("403 Forbidden - Authentication error")
                        logger.error(f"Request URL: {full_url}")
                        logger.error(f"Authorization header present: {'Authorization' in response.request.headers}")
                        logger.error(f"Check IAM permissions and API Gateway configuration")
                    
                    # Update circuit breaker state
                    self._handle_failure(response.status_code)
                    
                    # Client errors (except 429) shouldn't be retried
                    if 400 <= response.status_code < 500 and response.status_code != 429:
                        if retry_count >= self.max_retries:
                            response.raise_for_status()
                    else:
                        # Server errors and rate limiting should be retried
                        if retry_count >= self.max_retries:
                            response.raise_for_status()
                        
                        # Sleep and retry
                        retry_count += 1
                        logger.info(f"Retrying request ({retry_count}/{self.max_retries})...")
                        time.sleep(current_delay)
                        current_delay *= 2  # Exponential backoff
                        continue
                        
                    # For non-retryable errors, break the loop and raise the exception
                    response.raise_for_status()
            
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                # Network errors
                logger.error(f"Network error: {str(e)}")
                self._handle_failure()
                
                retry_count += 1
                if retry_count > self.max_retries:
                    raise
                
                logger.info(f"Retrying request ({retry_count}/{self.max_retries})...")
                time.sleep(current_delay)
                current_delay *= 2  # Exponential backoff
                
            except RequestException as e:
                # Other request errors
                logger.error(f"Request error: {str(e)}")
                self._handle_failure()
                
                retry_count += 1
                if retry_count > self.max_retries:
                    raise
                
                logger.info(f"Retrying request ({retry_count}/{self.max_retries})...")
                time.sleep(current_delay)
                current_delay *= 2  # Exponential backoff

    def _serialize_json_safe(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert data to be JSON serializable (especially UUIDs and datetimes).
        
        Args:
            data: Dictionary data to serialize
            
        Returns:
            Dictionary with JSON-serializable values
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, uuid.UUID):
                result[key] = str(value)
            elif isinstance(value, (datetime.datetime, datetime.date)):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = self._serialize_json_safe(value)
            elif isinstance(value, list):
                result[key] = [
                    self._serialize_json_safe(item) if isinstance(item, dict) else
                    str(item) if isinstance(item, uuid.UUID) else
                    item.isoformat() if isinstance(item, (datetime.datetime, datetime.date)) else
                    item
                    for item in value
                ]
            else:
                result[key] = value
        return result
    
    def check_paper_exists(self, arxiv_id: str) -> bool:
        """
        Check if a paper already exists in the database.
        
        Args:
            arxiv_id: ArXiv ID to check
            
        Returns:
            True if the paper exists, False otherwise
        """
        try:
            params = {"arxiv_identifier": arxiv_id}
            response = self._make_request('GET', '/papers', params=params)
            
            # Check if the response contains any papers
            if response and 'items' in response and response['items']:
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error checking if paper exists: {e}")
            # Assume it doesn't exist if we can't check
            return False
    
    def get_paper_id(self, arxiv_id: str) -> Optional[str]:
        """
        Get the database ID for a paper by ArXiv ID.
        
        Args:
            arxiv_id: ArXiv ID to look up
            
        Returns:
            Database paper ID if found, None otherwise
        """
        try:
            params = {"arxiv_identifier": arxiv_id}
            response = self._make_request('GET', '/papers', params=params)
            
            # Check if the response contains any papers
            if response and 'items' in response and response['items']:
                return response['items'][0]['paper_id']
            return None
            
        except Exception as e:
            logger.error(f"Error getting paper ID: {e}")
            return None
    
    def create_paper(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new paper in the database.
        
        Args:
            paper: Paper data
            
        Returns:
            Response from the API
        """
        return self._make_request('POST', '/papers', data=paper)
    
    def update_paper(self, paper_id: str, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing paper in the database.
        
        Args:
            paper_id: Database ID of the paper to update
            paper: Updated paper data
            
        Returns:
            Response from the API
        """
        return self._make_request('PUT', f'/papers/{paper_id}', data=paper)
    
    def upload_abstract(self, paper_id: str, abstract: str) -> Dict[str, Any]:
        """
        Upload a paper's abstract to S3 via the API.
        
        Args:
            paper_id: Database ID of the paper
            abstract: Abstract text
            
        Returns:
            Response from the API
        """
        data = {"abstract": abstract}
        return self._make_request('PUT', f'/papers/{paper_id}/abstract', data=data)
    
    def create_author(self, author: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new author in the database.
        
        Args:
            author: Author data
            
        Returns:
            Response from the API
        """
        return self._make_request('POST', '/authors', data=author)
    
    def create_paper_author(self, paper_author: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a paper-author relationship in the database.
        
        Args:
            paper_author: Paper-author relationship data
            
        Returns:
            Response from the API
        """
        return self._make_request('POST', '/papers/authors', data=paper_author)
    
    def create_category(self, category: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new category in the database.
        
        Args:
            category: Category data
            
        Returns:
            Response from the API
        """
        return self._make_request('POST', '/categories', data=category)
    
    def create_paper_category(self, paper_category: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a paper-category relationship in the database.
        
        Args:
            paper_category: Paper-category relationship data
            
        Returns:
            Response from the API
        """
        return self._make_request('POST', '/papers/categories', data=paper_category)
    
    def get_or_create_set(self, set_code: str, set_name: str) -> str:
        """
        Get or create an ArXiv set in the database.
        
        Args:
            set_code: Set code (e.g., 'cs')
            set_name: Set name (e.g., 'Computer Science')
            
        Returns:
            Set ID
        """
        try:
            # Check if set exists
            params = {"set_code": set_code}
            response = self._make_request('GET', '/sets', params=params)
            
            if response and 'items' in response and response['items']:
                return response['items'][0]['set_id']
            
            # Create the set
            set_data = {
                "set_code": set_code,
                "set_name": set_name
            }
            response = self._make_request('POST', '/sets', data=set_data)
            return response['set_id']
            
        except Exception as e:
            logger.error(f"Error getting or creating set: {e}")
            # Return a dummy UUID if we can't get or create the set
            return str(uuid.uuid4())
