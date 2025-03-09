#!/usr/bin/env python3
"""
API client for interacting with the ArXiv API Gateway
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional, Union
import uuid

import requests
from requests.exceptions import RequestException

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
        self.session = requests.Session()
        
        # Circuit breaker state
        self._failures = 0
        self._failure_threshold = 5
        self._circuit_open = False
        self._last_failure_time = 0
        self._circuit_reset_timeout = 30  # Reduced from 60 to 30 seconds for faster recovery
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
            
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        retry_count = 0
        current_delay = self.retry_delay
        
        # Handle JSON serialization issues with UUIDs
        if data:
            data = self._serialize_json_safe(data)
            
        while retry_count <= self.max_retries:
            try:
                headers = {"Content-Type": "application/json"}
                
                # Log the request for debugging
                if retry_count > 0:
                    logger.debug(f"Retry {retry_count}/{self.max_retries}: {method} {url}")
                else:
                    logger.debug(f"Request: {method} {url}")
                    
                # Make the request
                if method.upper() == 'GET':
                    response = self.session.get(url, params=params, headers=headers, timeout=10)
                elif method.upper() == 'POST':
                    response = self.session.post(url, json=data, headers=headers, timeout=10)
                elif method.upper() == 'PUT':
                    response = self.session.put(url, json=data, headers=headers, timeout=10)
                elif method.upper() == 'DELETE':
                    response = self.session.delete(url, headers=headers, timeout=10)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Check if we got a successful response
                if response.status_code < 200 or response.status_code >= 300:
                    logger.warning(
                        f"Request failed: {method} {url} - Status: {response.status_code} - Response: {response.text}"
                    )
                    
                    # Don't retry 4xx errors (except 429 Too Many Requests)
                    if 400 <= response.status_code < 500 and response.status_code != 429:
                        response.raise_for_status()
                    
                    # For 5xx errors, increment failure counter for circuit breaker
                    if 500 <= response.status_code < 600:
                        self._handle_failure(response.status_code)
                        
                        # If circuit breaker has opened, raise immediately
                        if self._circuit_open:
                            raise CircuitBreakerOpenError("Circuit breaker opened due to multiple server errors")
                    
                    # For other error codes, retry
                    retry_count += 1
                    if retry_count > self.max_retries:
                        response.raise_for_status()
                    
                    time.sleep(current_delay)
                    current_delay *= 2  # Exponential backoff
                    continue
                
                # Success - reset circuit breaker state
                self._handle_success()
                
                # Parse the response
                if response.text:
                    try:
                        return response.json()
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse JSON response: {response.text[:100]}...")
                        return {"raw_response": response.text}
                return {}
                
            except (requests.exceptions.ConnectTimeout, 
                    requests.exceptions.ReadTimeout,
                    requests.exceptions.ConnectionError) as e:
                # Network-level errors
                logger.error(f"Network error: {e}")
                self._handle_failure()
                
                # If circuit breaker has opened, raise immediately  
                if self._circuit_open:
                    raise CircuitBreakerOpenError("Circuit breaker opened due to network errors")
                
                retry_count += 1
                if retry_count > self.max_retries:
                    raise
                
                logger.info(f"Retrying request ({retry_count}/{self.max_retries})...")
                time.sleep(current_delay)
                current_delay *= 2  # Exponential backoff
            except RequestException as e:
                # Other request errors
                logger.error(f"Request error: {e}")
                self._handle_failure()
                
                # If circuit breaker has opened, raise immediately
                if self._circuit_open:
                    raise CircuitBreakerOpenError("Circuit breaker opened due to multiple failures")
                
                retry_count += 1
                if retry_count > self.max_retries:
                    raise
                
                logger.info(f"Retrying request ({retry_count}/{self.max_retries})...")
                time.sleep(current_delay)
                current_delay *= 2  # Exponential backoff

    def _serialize_json_safe(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert data to be JSON serializable (especially UUIDs).
        
        Args:
            data: Dictionary data to serialize
            
        Returns:
            Dictionary with JSON-serializable values
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, uuid.UUID):
                result[key] = str(value)
            elif isinstance(value, dict):
                result[key] = self._serialize_json_safe(value)
            elif isinstance(value, list):
                result[key] = [
                    self._serialize_json_safe(item) if isinstance(item, dict) else
                    str(item) if isinstance(item, uuid.UUID) else item
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
        return self._make_request('PUT', f'/abstracts/{paper_id}', data=data)
    
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