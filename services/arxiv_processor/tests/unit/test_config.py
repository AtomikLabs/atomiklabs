#!/usr/bin/env python3
"""
Unit tests for the configuration module
"""

import os
import json
from unittest.mock import patch, MagicMock, mock_open

import pytest

from src.config import ProcessorConfig, load_config


class TestProcessorConfig:
    """Tests for the ProcessorConfig class"""
    
    def test_init_default_values(self):
        """Test initialization with default values"""
        # Use a custom mock to return None for environment variables
        def mock_env_get(key, default=None):
            if key in ['ARXIV_CATEGORIES', 'ARXIV_SETS', 'DAYS_LOOKBACK', 'BATCH_SIZE', 'API_ENDPOINT', 'S3_ABSTRACT_PREFIX']:
                return None
            return default
            
        with patch('os.environ.get', side_effect=mock_env_get):
            config = ProcessorConfig()
            
            assert config.arxiv_categories == ['cs.AI', 'cs.CL', 'cs.CV', 'cs.CR', 'cs.RO']
            assert config.arxiv_sets == ['cs']
            assert config.days_lookback == 3
            assert config.batch_size == 10
            assert isinstance(config.api_endpoint, str)
            assert 'localhost' in config.api_endpoint
            assert config.s3_abstract_prefix == 'abstracts/'
    
    def test_load_from_env(self):
        """Test loading from environment variables"""
        # Mock environment variables
        mock_env = {
            'ARXIV_CATEGORIES': 'cs.AI,cs.CL',
            'ARXIV_SETS': 'cs',
            'DAYS_LOOKBACK': '1',
            'BATCH_SIZE': '2',
            'API_ENDPOINT': 'http://api.example.com',
            'S3_ABSTRACT_PREFIX': 'custom/abstracts/'
        }
        
        def mock_env_get(key, default=None):
            return mock_env.get(key, default)
            
        with patch('os.environ.get', side_effect=mock_env_get):
            config = ProcessorConfig()
            config.load_from_env()
            
            assert config.arxiv_categories == ['cs.AI', 'cs.CL']
            assert config.arxiv_sets == ['cs']
            assert config.days_lookback == 1
            assert config.batch_size == 2
            assert config.api_endpoint == 'http://api.example.com'
            assert config.s3_abstract_prefix == 'custom/abstracts/'
    
    def test_str_representation(self):
        """Test the string representation of the config"""
        config = ProcessorConfig()
        str_repr = str(config)
        
        assert 'arxiv_categories' in str_repr
        assert 'arxiv_sets' in str_repr
        assert 'days_lookback' in str_repr
        assert 'batch_size' in str_repr
        assert 'api_endpoint' in str_repr


def test_load_config_json():
    """Test loading config from JSON file"""
    # Mock the JSON data
    json_data = {
        "arxiv_categories": ["cs.AI", "cs.CL", "cs.CV"],
        "arxiv_sets": ["cs", "math"],
        "days_lookback": 5,
        "batch_size": 20,
        "s3_abstract_prefix": "papers/abstracts/"
    }
    
    # Create a mock for open to return our JSON data
    mock_file = mock_open(read_data=json.dumps(json_data))
    
    with patch('builtins.open', mock_file), \
         patch('os.environ.get', return_value=None):  # No env vars
        
        config = load_config()
        
        # Verify values from JSON were loaded
        assert config.arxiv_categories == ["cs.AI", "cs.CL", "cs.CV"]
        assert config.arxiv_sets == ["cs", "math"]
        assert config.days_lookback == 5
        assert config.batch_size == 20
        assert config.s3_abstract_prefix == "papers/abstracts/"


def test_load_config_json_error():
    """Test handling of JSON loading errors"""
    # Mock open to raise FileNotFoundError
    with patch('builtins.open', side_effect=FileNotFoundError()), \
         patch('logging.getLogger') as mock_logger:
        
        # Should fall back to environment variables
        config = load_config()
        
        # Verify we have a config with values from environment
        assert isinstance(config, ProcessorConfig)
        assert config.arxiv_categories == ['cs.AI', 'cs.CL']  # This comes from mock_os_environ_get in conftest.py
        assert config.days_lookback == 1  # This comes from mock_os_environ_get in conftest.py


def test_load_config_env_override():
    """Test environment variables overriding JSON config"""
    # Mock the JSON data
    json_data = {
        "arxiv_categories": ["cs.AI", "cs.CL", "cs.CV"],
        "arxiv_sets": ["cs", "math"],
        "days_lookback": 5,
        "batch_size": 20,
        "s3_abstract_prefix": "papers/abstracts/"
    }
    
    # Mock environment variables that will override JSON
    mock_env = {
        'API_ENDPOINT': 'http://api.example.com',
        'DAYS_LOOKBACK': '10'
    }
    
    def mock_env_get(key, default=None):
        return mock_env.get(key, default)
    
    # Create a mock for open to return our JSON data
    mock_file = mock_open(read_data=json.dumps(json_data))
    
    with patch('builtins.open', mock_file), \
         patch('os.environ.get', side_effect=mock_env_get):
        
        config = load_config()
        
        # Verify values from JSON were loaded
        assert config.arxiv_categories == ["cs.AI", "cs.CL", "cs.CV"]
        assert config.arxiv_sets == ["cs", "math"]
        assert config.batch_size == 20
        assert config.s3_abstract_prefix == "papers/abstracts/"
        
        # But environment variables took precedence
        assert config.api_endpoint == 'http://api.example.com'
        assert config.days_lookback == 10 