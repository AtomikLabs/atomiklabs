"""
Test script for the ArXiv processor
This script allows testing the processor without requiring AWS services.
"""

import os
import logging
import tempfile
from datetime import datetime, timedelta
import json

from atomiklabs_data import init_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from atomiklabs_data.models import Base

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample data to use for testing
SAMPLE_DATA = {
    "records": [
        {
            "identifier": "2401.12345",
            "date": datetime.now().date().isoformat(),
            "title": "Test Paper: Advanced Machine Learning Techniques",
            "authors": [
                {"first_name": "John", "last_name": "Smith"},
                {"first_name": "Jane", "last_name": "Doe"}
            ],
            "categories": ["LG", "AI", "CL"],
            "primary_category": "LG",
            "abstract": "This is a test abstract for a machine learning paper that discusses various advanced techniques.",
            "abstract_url": "https://arxiv.org/abs/2401.12345"
        },
        {
            "identifier": "2401.67890",
            "date": datetime.now().date().isoformat(),
            "title": "Natural Language Processing for Scientific Literature",
            "authors": [
                {"first_name": "Alice", "last_name": "Johnson"},
                {"first_name": "Bob", "last_name": "Williams"}
            ],
            "categories": ["CL", "IR"],
            "primary_category": "CL",
            "abstract": "This paper explores new methods for processing scientific literature using NLP techniques.",
            "abstract_url": "https://arxiv.org/abs/2401.67890"
        }
    ]
}

def setup_test_environment():
    """Set up a test environment with an in-memory SQLite database"""
    # Create a temporary directory for files
    temp_dir = tempfile.mkdtemp()
    
    # Set environment variables
    os.environ["CONFIG_PATH"] = "/dummy/path"
    os.environ["S3_BUCKET"] = temp_dir
    
    # Create an SQLite in-memory database
    engine = create_engine("sqlite:///:memory:", echo=True)
    Base.metadata.create_all(engine)
    
    # Create a session factory
    SessionLocal = sessionmaker(bind=engine)
    
    # Override functions that would access AWS services
    import processor
    
    # Original functions to restore later
    original_get_config = processor.get_config
    original_s3_upload = processor.upload_to_s3
    original_fetch_data = processor.fetch_data
    
    # Override get_config
    def mock_get_config():
        return {
            "categories": ["LG", "CL", "AI"],
            "back_date": 1,
            "set": "cs",
            "s3_bucket": temp_dir
        }
    processor.get_config = mock_get_config
    
    # Override upload_to_s3
    def mock_upload_to_s3(file_data, key):
        logger.info(f"Mock S3 upload: {key}")
        # Save to temp directory
        file_path = os.path.join(temp_dir, key)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(file_data.read())
    processor.upload_to_s3 = mock_upload_to_s3
    
    # Override fetch_data to return our sample data
    def mock_fetch_data(base_url, from_date):
        logger.info(f"Mock fetch data for date: {from_date}")
        # Generate sample XML
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
          <ListRecords>
            <record>
              <header>
                <identifier>oai:arXiv.org:2401.12345</identifier>
                <datestamp>2024-01-15T12:00:00Z</datestamp>
                <setSpec>cs.LG</setSpec>
                <setSpec>cs.AI</setSpec>
                <setSpec>cs.CL</setSpec>
              </header>
              <metadata>
                <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" 
                           xmlns:dc="http://purl.org/dc/elements/1.1/">
                  <dc:title>Test Paper: Advanced Machine Learning Techniques</dc:title>
                  <dc:creator>Smith, John</dc:creator>
                  <dc:creator>Doe, Jane</dc:creator>
                  <dc:description>This is a test abstract for a machine learning paper that discusses various advanced techniques.</dc:description>
                  <dc:date>2024-01-15</dc:date>
                </oai_dc:dc>
              </metadata>
            </record>
            <record>
              <header>
                <identifier>oai:arXiv.org:2401.67890</identifier>
                <datestamp>2024-01-15T14:30:00Z</datestamp>
                <setSpec>cs.CL</setSpec>
                <setSpec>cs.IR</setSpec>
              </header>
              <metadata>
                <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" 
                           xmlns:dc="http://purl.org/dc/elements/1.1/">
                  <dc:title>Natural Language Processing for Scientific Literature</dc:title>
                  <dc:creator>Johnson, Alice</dc:creator>
                  <dc:creator>Williams, Bob</dc:creator>
                  <dc:description>This paper explores new methods for processing scientific literature using NLP techniques.</dc:description>
                  <dc:date>2024-01-15</dc:date>
                </oai_dc:dc>
              </metadata>
            </record>
          </ListRecords>
        </OAI-PMH>
        """
        return [xml]
    processor.fetch_data = mock_fetch_data
    
    # Override the database initialization in processor
    def init_test_db():
        processor.get_session = lambda: SessionLocal()
    
    # Set up database session
    init_test_db()
    
    # Function to restore original functions
    def restore_functions():
        processor.get_config = original_get_config
        processor.upload_to_s3 = original_s3_upload
        processor.fetch_data = original_fetch_data
    
    return {
        "temp_dir": temp_dir,
        "engine": engine,
        "session_factory": SessionLocal,
        "restore_functions": restore_functions
    }

def main():
    """Run the test"""
    logger.info("Setting up test environment")
    test_env = setup_test_environment()
    
    try:
        logger.info("Running processor...")
        import processor
        result = processor.main()
        
        logger.info("Processor completed successfully")
        logger.info(f"Result: {result}")
        
        # Check the temp directory for saved files
        temp_files = []
        for root, dirs, files in os.walk(test_env["temp_dir"]):
            for file in files:
                temp_files.append(os.path.join(root, file))
        
        logger.info(f"Generated files: {temp_files}")
        
    finally:
        # Clean up
        import shutil
        shutil.rmtree(test_env["temp_dir"])
        logger.info("Test environment cleaned up")

if __name__ == "__main__":
    main() 