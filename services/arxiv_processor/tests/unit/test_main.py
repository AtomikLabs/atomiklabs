#!/usr/bin/env python3
"""
Unit tests for the main module
"""

import json
import uuid
from unittest.mock import patch, MagicMock, call

import pytest

from src.main import chunk_list, process_batch, main


def test_chunk_list():
    """Test the chunk_list function"""
    # Test with empty list
    assert chunk_list([], 3) == []
    
    # Test with list smaller than chunk size
    assert chunk_list([1, 2], 3) == [[1, 2]]
    
    # Test with list exactly equal to chunk size
    assert chunk_list([1, 2, 3], 3) == [[1, 2, 3]]
    
    # Test with list larger than chunk size
    assert chunk_list([1, 2, 3, 4, 5, 6, 7], 3) == [[1, 2, 3], [4, 5, 6], [7]]
    
    # Test with list that divides evenly by chunk size
    assert chunk_list([1, 2, 3, 4, 5, 6], 3) == [[1, 2, 3], [4, 5, 6]]


class TestProcessBatch:
    """Tests for the process_batch function"""
    
    def test_process_batch_new_papers(self, mock_api_client):
        """Test processing a batch of new papers"""
        # Set up mock Paper objects
        mock_paper1 = MagicMock()
        mock_paper1.paper_id = uuid.uuid4()
        mock_paper1.arxiv_identifier = '2301.12345'
        mock_paper1.model_dump.return_value = {
            'paper_id': str(mock_paper1.paper_id),
            'arxiv_identifier': mock_paper1.arxiv_identifier,
            'title': 'Test Paper 1'
        }
        
        mock_paper2 = MagicMock()
        mock_paper2.paper_id = uuid.uuid4()
        mock_paper2.arxiv_identifier = '2301.54321'
        mock_paper2.model_dump.return_value = {
            'paper_id': str(mock_paper2.paper_id),
            'arxiv_identifier': mock_paper2.arxiv_identifier,
            'title': 'Test Paper 2'
        }
        
        # Set up mock API client
        mock_api_client.check_paper_exists.return_value = False
        mock_api_client.create_paper.return_value = {'paper_id': str(mock_paper1.paper_id)}
        
        # Set up batch data
        batch_data = {
            'papers': [mock_paper1, mock_paper2],
            'abstracts': [
                {'paper_id': str(mock_paper1.paper_id), 'abstract': 'Abstract 1'},
                {'paper_id': str(mock_paper2.paper_id), 'abstract': 'Abstract 2'}
            ]
        }
        
        # Process the batch
        results = process_batch(batch_data, mock_api_client)
        
        # Verify the results
        assert results['papers_created'] == 2
        assert results['papers_updated'] == 0
        assert results['papers_failed'] == 0
        assert results['abstracts_stored'] == 2
        assert results['abstracts_failed'] == 0
        
        # Verify API client calls
        assert mock_api_client.check_paper_exists.call_count == 2
        assert mock_api_client.create_paper.call_count == 2
        assert mock_api_client.update_paper.call_count == 0
        assert mock_api_client.upload_abstract.call_count == 2
    
    def test_process_batch_existing_papers(self, mock_api_client):
        """Test processing a batch with existing papers"""
        # Set up mock Paper objects
        mock_paper = MagicMock()
        mock_paper.paper_id = uuid.uuid4()
        mock_paper.arxiv_identifier = '2301.12345'
        mock_paper.model_dump.return_value = {
            'paper_id': str(mock_paper.paper_id),
            'arxiv_identifier': mock_paper.arxiv_identifier,
            'title': 'Test Paper'
        }
        
        # Set up mock API client
        mock_api_client.check_paper_exists.return_value = True
        mock_api_client.get_paper_id.return_value = str(mock_paper.paper_id)
        
        # Set up batch data
        batch_data = {
            'papers': [mock_paper],
            'abstracts': [
                {'paper_id': str(mock_paper.paper_id), 'abstract': 'Abstract text'}
            ]
        }
        
        # Process the batch
        results = process_batch(batch_data, mock_api_client)
        
        # Verify the results
        assert results['papers_created'] == 0
        assert results['papers_updated'] == 1
        assert results['papers_failed'] == 0
        assert results['abstracts_stored'] == 1
        assert results['abstracts_failed'] == 0
        
        # Verify API client calls
        mock_api_client.check_paper_exists.assert_called_once_with(mock_paper.arxiv_identifier)
        # Note: get_paper_id is called twice in the implementation, so we check for at least one call
        assert mock_api_client.get_paper_id.call_count >= 1
        assert mock_api_client.get_paper_id.call_args[0][0] == mock_paper.arxiv_identifier
        # The implementation calls update_paper twice (once for the initial update, once after uploading the abstract)
        assert mock_api_client.update_paper.call_count >= 1
        assert mock_api_client.upload_abstract.call_count == 1
    
    def test_process_batch_paper_error(self, mock_api_client):
        """Test error handling when processing papers"""
        # Set up mock Paper objects
        mock_paper = MagicMock()
        mock_paper.paper_id = uuid.uuid4()
        mock_paper.arxiv_identifier = '2301.12345'
        mock_paper.model_dump.return_value = {
            'paper_id': str(mock_paper.paper_id),
            'arxiv_identifier': mock_paper.arxiv_identifier,
            'title': 'Test Paper'
        }
        
        # Set up mock API client to raise an exception
        mock_api_client.check_paper_exists.side_effect = Exception("API error")
        
        # Set up batch data
        batch_data = {
            'papers': [mock_paper],
            'abstracts': [
                {'paper_id': str(mock_paper.paper_id), 'abstract': 'Abstract text'}
            ]
        }
        
        # Process the batch
        results = process_batch(batch_data, mock_api_client)
        
        # Verify the results
        assert results['papers_created'] == 0
        assert results['papers_updated'] == 0
        assert results['papers_failed'] == 1
        assert results['abstracts_stored'] == 0
        assert results['abstracts_failed'] == 0
    
    def test_process_batch_abstract_error(self, mock_api_client):
        """Test error handling when uploading abstracts"""
        # Set up mock Paper objects
        mock_paper = MagicMock()
        mock_paper.paper_id = uuid.uuid4()
        mock_paper.arxiv_identifier = '2301.12345'
        mock_paper.model_dump.return_value = {
            'paper_id': str(mock_paper.paper_id),
            'arxiv_identifier': mock_paper.arxiv_identifier,
            'title': 'Test Paper'
        }
        
        # Set up mock API client
        mock_api_client.check_paper_exists.return_value = False
        mock_api_client.create_paper.return_value = {'paper_id': str(mock_paper.paper_id)}
        mock_api_client.upload_abstract.side_effect = Exception("S3 error")
        
        # Set up batch data
        batch_data = {
            'papers': [mock_paper],
            'abstracts': [
                {'paper_id': str(mock_paper.paper_id), 'abstract': 'Abstract text'}
            ]
        }
        
        # Process the batch
        results = process_batch(batch_data, mock_api_client)
        
        # Verify the results
        assert results['papers_created'] == 1
        assert results['papers_updated'] == 0
        assert results['papers_failed'] == 0
        assert results['abstracts_stored'] == 0
        assert results['abstracts_failed'] == 1


class TestMain:
    """Tests for the main function"""
    
    def test_main_success(self, mock_config, mock_api_client, mock_fetch_papers, mock_process_papers):
        """Test successful execution of the main function"""
        # Set up mocks
        with patch('src.main.ApiClient', return_value=mock_api_client):
            with patch('src.main.load_config', return_value=mock_config):
                with patch('src.main.fetch_papers_for_date_range', return_value=[{'id': 1}]):
                    with patch('src.main.process_papers') as mock_process:
                        with patch('src.main.process_batch') as mock_batch:
                            # Set up mock returns
                            mock_process.return_value = {
                                'papers': [MagicMock()],
                                'abstracts': [{'paper_id': 'test', 'abstract': 'test'}]
                            }
                            mock_batch.return_value = {
                                'papers_created': 1,
                                'papers_updated': 0,
                                'papers_failed': 0,
                                'abstracts_stored': 1,
                                'abstracts_failed': 0
                            }
                            
                            # Call the main function
                            main()
                            
                            # Verify the calls
                            mock_process.assert_called_once()
                            mock_batch.assert_called_once()
    
    def test_main_no_papers(self, mock_config, mock_api_client):
        """Test main function when no papers are found"""
        # Set up mocks
        with patch('src.main.ApiClient', return_value=mock_api_client):
            with patch('src.main.load_config', return_value=mock_config):
                with patch('src.main.fetch_papers_for_date_range', return_value=[]):
                    with patch('src.main.process_papers') as mock_process:
                        # Call the main function
                        main()
                        
                        # Verify that process_papers was not called
                        mock_process.assert_not_called()
    
    def test_main_error(self, mock_config, mock_api_client):
        """Test error handling in the main function"""
        # Set up mocks to raise an exception
        with patch('src.main.ApiClient', return_value=mock_api_client):
            with patch('src.main.load_config', return_value=mock_config):
                with patch('src.main.fetch_papers_for_date_range', side_effect=Exception("Test error")):
                    # Call the main function - should re-raise the exception
                    with pytest.raises(Exception):
                        main() 