#!/usr/bin/env python3
"""
Unit tests for the ArXiv fetcher module
"""

import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock, Mock

import pytest
import requests
from defusedxml.ElementTree import ParseError

from src.arxiv_fetcher import (
    fetch_papers_for_date_range,
    fetch_data,
    parse_xml_data,
    latex_to_human_readable,
    CS_CATEGORIES_INVERTED
)


class TestFetchPapersForDateRange:
    """Tests for fetch_papers_for_date_range function"""
    
    def test_fetch_papers_success(self, mock_requests_get):
        """Test successful paper fetching"""
        # Mock the fetch_data and parse_xml_data functions
        with patch('src.arxiv_fetcher.fetch_data') as mock_fetch:
            with patch('src.arxiv_fetcher.parse_xml_data') as mock_parse:
                # Set up the mocks
                mock_fetch.return_value = ['<xml>test</xml>']
                mock_parse.return_value = {
                    'records': [
                        {
                            'identifier': 'test-id',
                            'abstract_url': 'https://arxiv.org/abs/test',
                            'primary_category': 'AI',
                            'categories': ['AI', 'CL'],
                            'abstract': 'Test abstract',
                            'title': 'Test Title',
                            'date': '2023-01-01',
                        }
                    ]
                }
                
                # Call the function
                results = fetch_papers_for_date_range(
                    sets=['cs'],
                    categories=['cs.AI', 'cs.CL'],
                    days_lookback=1
                )
                
                # Check the results
                assert len(results) == 1
                assert results[0]['identifier'] == 'test-id'
                assert results[0]['primary_category'] == 'AI'
                
                # Verify fetch_data was called with correct parameters
                mock_fetch.assert_called_once()
                args, kwargs = mock_fetch.call_args
                assert args[1].startswith('20')  # Date should be in YYYY-MM-DD format
                assert args[2] == 'cs'
                
                # Verify parse_xml_data was called with the XML data
                mock_parse.assert_called_once_with('<xml>test</xml>', ['AI', 'CL'])
    
    def test_fetch_papers_no_results(self, mock_requests_get):
        """Test when no papers are found"""
        # Mock the fetch_data and parse_xml_data functions
        with patch('src.arxiv_fetcher.fetch_data') as mock_fetch:
            with patch('src.arxiv_fetcher.parse_xml_data') as mock_parse:
                # Set up the mocks to return no data
                mock_fetch.return_value = []
                
                # Call the function
                results = fetch_papers_for_date_range(
                    sets=['cs'],
                    categories=['cs.AI'],
                    days_lookback=1
                )
                
                # Check the results
                assert results == []
                
                # Verify fetch_data was called
                mock_fetch.assert_called_once()
                
                # parse_xml_data should not be called if fetch_data returns no data
                mock_parse.assert_not_called()


class TestFetchData:
    """Tests for fetch_data function"""
    
    def test_fetch_data_success(self, mock_requests_get):
        """Test successful data fetching"""
        # Mock the requests.get response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<test>xml</test>"
        mock_response.content = b"<test>xml</test>"
        mock_requests_get.return_value = mock_response
        
        # Mock ET.fromstring to return a mock element
        with patch('defusedxml.ElementTree.fromstring') as mock_fromstring:
            mock_root = MagicMock()
            mock_root.find.return_value = None  # No resumption token
            mock_fromstring.return_value = mock_root
            
            # Call the function
            results = fetch_data("http://example.com", "2023-01-01", "cs")
            
            # Check the results
            assert len(results) == 1
            assert results[0] == "<test>xml</test>"
            
            # Verify requests.get was called with correct parameters
            mock_requests_get.assert_called_once()
            args, kwargs = mock_requests_get.call_args
            assert args[0] == "http://example.com"
            assert kwargs['params'] == {
                "verb": "ListRecords",
                "set": "cs",
                "metadataPrefix": "oai_dc",
                "from": "2023-01-01"
            }
    
    def test_fetch_data_with_resumption_token(self, mock_requests_get):
        """Test data fetching with resumption token"""
        # Create two mock responses for pagination
        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.text = "<test>xml1</test>"
        mock_response1.content = b"<test>xml1</test>"
        
        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.text = "<test>xml2</test>"
        mock_response2.content = b"<test>xml2</test>"
        
        mock_requests_get.side_effect = [mock_response1, mock_response2]
        
        # Mock ET.fromstring to return a mock element with resumption token for first call,
        # and without resumption token for second call
        with patch('defusedxml.ElementTree.fromstring') as mock_fromstring:
            # First response has resumption token
            mock_root1 = MagicMock()
            mock_token1 = MagicMock()
            mock_token1.text = "token123"
            mock_root1.find.return_value = mock_token1
            
            # Second response has no resumption token
            mock_root2 = MagicMock()
            mock_root2.find.return_value = None
            
            mock_fromstring.side_effect = [mock_root1, mock_root2]
            
            # Call the function
            results = fetch_data("http://example.com", "2023-01-01", "cs")
            
            # Check the results
            assert len(results) == 2
            assert results[0] == "<test>xml1</test>"
            assert results[1] == "<test>xml2</test>"
            
            # Verify requests.get was called twice with correct parameters
            assert mock_requests_get.call_count == 2
            
            # First call should use initial parameters
            args1, kwargs1 = mock_requests_get.call_args_list[0]
            assert args1[0] == "http://example.com"
            assert kwargs1['params'] == {
                "verb": "ListRecords",
                "set": "cs",
                "metadataPrefix": "oai_dc",
                "from": "2023-01-01"
            }
            
            # Second call should use resumption token
            args2, kwargs2 = mock_requests_get.call_args_list[1]
            assert args2[0] == "http://example.com"
            assert kwargs2['params'] == {
                "verb": "ListRecords",
                "resumptionToken": "token123"
            }
    
    def test_fetch_data_503_error(self, mock_requests_get):
        """Test handling of 503 errors"""
        # Mock a 503 response followed by a successful response
        mock_response_503 = MagicMock()
        mock_response_503.status_code = 503
        mock_response_503.headers = {"Retry-After": "1"}  # Short delay for testing
        
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.text = "<test>xml</test>"
        mock_response_success.content = b"<test>xml</test>"
        
        mock_requests_get.side_effect = [mock_response_503, mock_response_success]
        
        # Mock ET.fromstring for the successful response
        with patch('defusedxml.ElementTree.fromstring') as mock_fromstring:
            mock_root = MagicMock()
            mock_root.find.return_value = None
            mock_fromstring.return_value = mock_root
            
            # Call the function
            with patch('time.sleep') as mock_sleep:  # Mock sleep to avoid delays
                results = fetch_data("http://example.com", "2023-01-01", "cs")
                
                # Verify sleep was called with the retry time
                mock_sleep.assert_called_once_with(1)
            
            # Check the results
            assert len(results) == 1
            assert results[0] == "<test>xml</test>"
            
            # Verify requests.get was called twice
            assert mock_requests_get.call_count == 2


class TestParseXmlData:
    """Tests for parse_xml_data function"""
    
    def test_parse_xml_data_success(self):
        """Test successful XML parsing"""
        # Sample XML content
        xml_data = """
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:dc="http://purl.org/dc/elements/1.1/">
            <ListRecords>
                <record>
                    <header>
                        <identifier>oai:arXiv.org:2301.12345</identifier>
                    </header>
                    <metadata>
                        <dc:identifier>https://arxiv.org/abs/2301.12345</dc:identifier>
                        <dc:title>Sample Paper Title</dc:title>
                        <dc:description>This is a sample abstract.</dc:description>
                        <dc:creator>Doe, Jane</dc:creator>
                        <dc:creator>Smith, John</dc:creator>
                        <dc:subject>Computer Science - Artifical Intelligence</dc:subject>
                        <dc:date>2023-01-15</dc:date>
                    </metadata>
                </record>
            </ListRecords>
        </OAI-PMH>
        """
        
        # Call the function
        with patch('defusedxml.ElementTree.fromstring') as mock_fromstring:
            # Create mock elements to return when parsing
            mock_root = MagicMock()
            mock_record = MagicMock()
            mock_identifier = MagicMock(text="oai:arXiv.org:2301.12345")
            mock_abs_url = MagicMock(text="https://arxiv.org/abs/2301.12345")
            mock_title = MagicMock(text="Sample Paper Title")
            mock_abstract = MagicMock(text="This is a sample abstract.")
            mock_date = MagicMock(text="2023-01-15")
            mock_creator1 = MagicMock(text="Doe, Jane")
            mock_creator2 = MagicMock(text="Smith, John")
            mock_subject = MagicMock(text="Computer Science - Artifical Intelligence")
            
            # Set up the mock relationships
            mock_root.findall.return_value = [mock_record]
            mock_record.find.side_effect = lambda path, ns: {
                ".//oai:identifier": mock_identifier,
                ".//dc:identifier": mock_abs_url,
                ".//dc:title": mock_title,
                ".//dc:description": mock_abstract,
                ".//dc:date": mock_date
            }.get(path, None)
            mock_record.findall.side_effect = lambda path, ns: {
                ".//dc:creator": [mock_creator1, mock_creator2],
                ".//dc:subject": [mock_subject]
            }.get(path, [])
            
            mock_fromstring.return_value = mock_root
            
            # Call the function
            result = parse_xml_data(xml_data)
            
            # Check the results
            assert 'records' in result
            assert len(result['records']) == 1
            
            record = result['records'][0]
            assert record['identifier'] == "oai:arXiv.org:2301.12345"
            assert record['abstract_url'] == "https://arxiv.org/abs/2301.12345"
            assert record['title'] == "Sample Paper Title"
            assert record['abstract'] == "This is a sample abstract."
            assert record['date'] == "2023-01-15"
            assert record['primary_category'] == "AI"
            assert record['categories'] == ["AI"]
            assert len(record['authors']) == 2
            assert record['authors'][0]['last_name'] == "Doe"
            assert record['authors'][0]['first_name'] == "Jane"
            assert record['authors'][1]['last_name'] == "Smith"
            assert record['authors'][1]['first_name'] == "John"
    
    def test_parse_xml_data_with_filter(self):
        """Test XML parsing with category filtering"""
        xml_data = "<test>xml</test>"
        
        # Set up the mocks
        with patch('defusedxml.ElementTree.fromstring') as mock_fromstring:
            # Create mock elements as before, but with a different category
            mock_root = MagicMock()
            mock_record = MagicMock()
            mock_identifier = MagicMock(text="oai:arXiv.org:2301.12345")
            mock_abs_url = MagicMock(text="https://arxiv.org/abs/2301.12345")
            mock_title = MagicMock(text="Sample Paper Title")
            mock_abstract = MagicMock(text="This is a sample abstract.")
            mock_date = MagicMock(text="2023-01-15")
            mock_creator = MagicMock(text="Doe, Jane")
            mock_subject = MagicMock(text="Computer Science - Computation and Language")
            
            # Set up the mock relationships
            mock_root.findall.return_value = [mock_record]
            mock_record.find.side_effect = lambda path, ns: {
                ".//oai:identifier": mock_identifier,
                ".//dc:identifier": mock_abs_url,
                ".//dc:title": mock_title,
                ".//dc:description": mock_abstract,
                ".//dc:date": mock_date
            }.get(path, None)
            mock_record.findall.side_effect = lambda path, ns: {
                ".//dc:creator": [mock_creator],
                ".//dc:subject": [mock_subject]
            }.get(path, [])
            
            mock_fromstring.return_value = mock_root
            
            # Call the function with a filter for AI only
            result = parse_xml_data(xml_data, filter_categories=["AI"])
            
            # Since the record has category CL, it should be filtered out
            assert len(result['records']) == 0
            
            # Now try with a filter that includes CL
            result = parse_xml_data(xml_data, filter_categories=["CL"])
            
            # Now the record should be included
            assert len(result['records']) == 1
            record = result['records'][0]
            assert record['primary_category'] == "CL"
    
    def test_parse_xml_data_error(self):
        """Test handling of XML parsing errors"""
        xml_data = "invalid xml"
        
        # Mock ET.fromstring to raise a ParseError
        with patch('defusedxml.ElementTree.fromstring') as mock_fromstring:
            mock_fromstring.side_effect = ParseError("XML parsing error")
            
            # Call the function
            result = parse_xml_data(xml_data)
            
            # Should return empty records on error
            assert result == {"records": []}


class TestLatexToHumanReadable:
    """Tests for latex_to_human_readable function"""
    
    def test_latex_to_human_readable_basic(self):
        """Test basic LaTeX conversion"""
        latex = "This is a test with $\\alpha$ and $\\beta$."
        result = latex_to_human_readable(latex)
        
        assert result == "This is a test with alpha and beta."
    
    def test_latex_to_human_readable_complex(self):
        """Test more complex LaTeX conversion"""
        latex = "The formula $E = mc^2$ shows that $E \\geq 0$ for $m \\geq 0$."
        result = latex_to_human_readable(latex)
        
        assert "E = mc" in result
        assert ">=" in result
    
    def test_latex_to_human_readable_empty(self):
        """Test conversion of empty string"""
        result = latex_to_human_readable("")
        assert result == ""
        
        result = latex_to_human_readable(None)
        assert result == "" 