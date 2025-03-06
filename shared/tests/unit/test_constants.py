import pytest
from constants import enums
from constants.paths import (
    S3_ABSTRACT_PREFIX,
    S3_PAPER_PREFIX,
    S3_METADATA_PREFIX,
    S3_ABSTRACT_PATH_TEMPLATE,
    API_PAPERS_PATH
)

def test_enums_exist():
    """Test that the main enums are defined and accessible."""
    assert hasattr(enums, 'IngestionStatus')

def test_enum_values():
    """Test that enum values are as expected."""
    assert enums.IngestionStatus.IN_PROGRESS.value == "in_progress"
    assert enums.IngestionStatus.COMPLETED.value == "completed"
    assert enums.IngestionStatus.FAILED.value == "failed"
    
def test_s3_path_prefixes():
    """Test that S3 path prefixes are properly defined."""
    assert S3_ABSTRACT_PREFIX == "abstracts"
    assert S3_PAPER_PREFIX == "papers"
    assert S3_METADATA_PREFIX == "metadata"
    
def test_path_templates():
    """Test that path templates are properly formatted."""
    # Test template formatting with sample values
    abstract_path = S3_ABSTRACT_PATH_TEMPLATE.format(
        set_code="cs",
        year="2023",
        month="01",
        day="15",
        arxiv_id="2301.12345"
    )
    assert abstract_path == "abstracts/cs/2023/01/15/2301.12345.txt"
    
def test_api_paths():
    """Test that API paths are properly defined."""
    assert API_PAPERS_PATH == "papers" 