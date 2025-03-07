#!/usr/bin/env python3
"""
Unit tests for the configuration module
"""

import os
from unittest.mock import patch, MagicMock

import pytest
from botocore.exceptions import ClientError

from src.config import ProcessorConfig, load_config


class TestProcessorConfig:
    """Tests for the ProcessorConfig class"""
    
    def test_init_default_values(self):
        """Test initialization with default values"""
        # Use a custom mock to return None for environment variables but default values for others
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
        # Environment variables are already mocked in conftest.py
        config = ProcessorConfig()
        
        assert config.arxiv_categories == ['cs.AI', 'cs.CL']
        assert config.arxiv_sets == ['cs']
        assert config.days_lookback == 1
        assert config.batch_size == 2
        assert config.api_endpoint == 'http://localhost:8080'
    
    def test_load_from_ssm(self):
        """Test loading from SSM Parameter Store"""
        # Create a mock SSM client
        mock_ssm = MagicMock()
        mock_ssm.get_parameters_by_path.return_value = {
            'Parameters': [
                {'Name': '/test/config/arxiv_categories', 'Value': 'cs.AI,cs.CL,cs.CV'},
                {'Name': '/test/config/arxiv_sets', 'Value': 'cs,math'},
                {'Name': '/test/config/days_lookback', 'Value': '5'},
                {'Name': '/test/config/batch_size', 'Value': '20'},
                {'Name': '/test/config/api_endpoint', 'Value': 'https://api.example.com'},
                {'Name': '/test/config/s3_abstract_prefix', 'Value': 'papers/abstracts/'},
            ]
        }
        
        # Patch boto3.client to return our mock
        with patch('boto3.client', return_value=mock_ssm):
            config = ProcessorConfig()
            config.load_from_ssm('/test/config')
            
            assert config.arxiv_categories == ['cs.AI', 'cs.CL', 'cs.CV']
            assert config.arxiv_sets == ['cs', 'math']
            assert config.days_lookback == 5
            assert config.batch_size == 20
            assert config.api_endpoint == 'https://api.example.com'
            assert config.s3_abstract_prefix == 'papers/abstracts/'
    
    def test_load_from_ssm_error(self):
        """Test error handling when loading from SSM"""
        # Create a mock SSM client that raises an error
        mock_ssm = MagicMock()
        mock_ssm.get_parameters_by_path.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            'GetParametersByPath'
        )
        
        # Patch boto3.client to return our mock
        with patch('boto3.client', return_value=mock_ssm):
            config = ProcessorConfig()
            
            # Should not raise an exception, just log and fallback to env
            config.load_from_ssm('/test/config')
            
            # Should still have values from environment
            assert config.arxiv_categories == ['cs.AI', 'cs.CL']
            assert config.days_lookback == 1
    
    def test_str_representation(self):
        """Test the string representation of the config"""
        config = ProcessorConfig()
        str_repr = str(config)
        
        assert 'arxiv_categories' in str_repr
        assert 'arxiv_sets' in str_repr
        assert 'days_lookback' in str_repr
        assert 'batch_size' in str_repr
        assert 'api_endpoint' in str_repr


def test_load_config():
    """Test the load_config function"""
    # Mock the SSM path
    with patch('os.environ.get') as mock_env_get:
        mock_env_get.return_value = '/test/config'
        with patch.object(ProcessorConfig, 'load_from_ssm') as mock_load_from_ssm:
            with patch.object(ProcessorConfig, 'load_from_env'):
                config = load_config()
                
                # Check that load_from_ssm was called
                mock_load_from_ssm.assert_called_once_with('/test/config')
                
                # Check that we got a ProcessorConfig instance
                assert isinstance(config, ProcessorConfig) 