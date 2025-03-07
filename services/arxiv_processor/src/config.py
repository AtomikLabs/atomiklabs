#!/usr/bin/env python3
"""
Configuration for the ArXiv processor

This module loads configuration from a JSON file and environment variables.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional

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
    """Load configuration from JSON file and environment variables."""
    config = ProcessorConfig()
    
    # Try to load from JSON file first
    try:
        with open('/app/config.json', 'r') as f:
            config_data = json.load(f)
            config.arxiv_categories = config_data.get('arxiv_categories', config.arxiv_categories)
            config.arxiv_sets = config_data.get('arxiv_sets', config.arxiv_sets)
            config.days_lookback = config_data.get('days_lookback', config.days_lookback)
            config.batch_size = config_data.get('batch_size', config.batch_size)
            config.s3_abstract_prefix = config_data.get('s3_abstract_prefix', config.s3_abstract_prefix)
            logger.info("Loaded configuration from JSON file")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Could not load config from JSON: {e}, falling back to defaults")
    
    # Always check environment variables (override JSON config)
    config.load_from_env()
    
    logger.info(f"Loaded configuration: {config}")
    return config 