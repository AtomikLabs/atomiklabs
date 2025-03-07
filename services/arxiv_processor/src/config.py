#!/usr/bin/env python3
"""
Configuration for the ArXiv processor

This module loads configuration from environment variables or a config file.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class ProcessorConfig:
    """Configuration for the ArXiv processor."""
    
    def __init__(self):
        # Default values
        self.arxiv_categories: List[str] = ['cs.AI', 'cs.CL', 'cs.CV', 'cs.CR', 'cs.RO']
        self.arxiv_sets: List[str] = ['cs']
        self.days_lookback: int = 3
        self.batch_size: int = 10
        self.api_endpoint: str = 'http://localhost:8080'  # Default value
        self.s3_abstract_prefix: str = 'abstracts/'
        self.load_from_env()
    
    def load_from_env(self) -> None:
        """Load configuration from environment variables."""
        if os.environ.get('ARXIV_CATEGORIES'):
            self.arxiv_categories = os.environ.get('ARXIV_CATEGORIES', '').split(',')
        
        if os.environ.get('ARXIV_SETS'):
            self.arxiv_sets = os.environ.get('ARXIV_SETS', '').split(',')
        
        if os.environ.get('DAYS_LOOKBACK'):
            self.days_lookback = int(os.environ.get('DAYS_LOOKBACK', '3'))
        
        if os.environ.get('BATCH_SIZE'):
            self.batch_size = int(os.environ.get('BATCH_SIZE', '10'))
        
        if os.environ.get('API_ENDPOINT'):
            self.api_endpoint = os.environ.get('API_ENDPOINT', 'http://localhost:8080')
        
        if os.environ.get('S3_ABSTRACT_PREFIX'):
            self.s3_abstract_prefix = os.environ.get('S3_ABSTRACT_PREFIX', 'abstracts/')

    def load_from_ssm(self, ssm_path: str) -> None:
        """Load configuration from AWS SSM Parameter Store."""
        try:
            ssm = boto3.client('ssm')
            # Get all parameters under the given path
            response = ssm.get_parameters_by_path(
                Path=ssm_path,
                Recursive=True,
                WithDecryption=True
            )
            
            for param in response.get('Parameters', []):
                name = param['Name'].split('/')[-1]  # Get the last part of the path
                value = param['Value']
                
                if name == 'arxiv_categories':
                    self.arxiv_categories = value.split(',')
                elif name == 'arxiv_sets':
                    self.arxiv_sets = value.split(',')
                elif name == 'days_lookback':
                    self.days_lookback = int(value)
                elif name == 'batch_size':
                    self.batch_size = int(value)
                elif name == 'api_endpoint':
                    self.api_endpoint = value
                elif name == 's3_abstract_prefix':
                    self.s3_abstract_prefix = value
                    
            logger.info(f"Loaded configuration from SSM path: {ssm_path}")
            
        except ClientError as e:
            logger.error(f"Error loading configuration from SSM: {e}")
            # Fall back to environment variables
            logger.info("Falling back to environment variables for configuration")
    
    def __str__(self) -> str:
        """Return a string representation of the configuration."""
        return json.dumps({
            'arxiv_categories': self.arxiv_categories,
            'arxiv_sets': self.arxiv_sets,
            'days_lookback': self.days_lookback,
            'batch_size': self.batch_size,
            'api_endpoint': self.api_endpoint,
            's3_abstract_prefix': self.s3_abstract_prefix
        }, indent=2)


def load_config() -> ProcessorConfig:
    """Load configuration from environment variables or SSM."""
    config = ProcessorConfig()
    
    # Check if we should load from SSM
    ssm_path = os.environ.get('CONFIG_SSM_PATH')
    if ssm_path:
        config.load_from_ssm(ssm_path)
    
    logger.info(f"Loaded configuration: {config}")
    return config 