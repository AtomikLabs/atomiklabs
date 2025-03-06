import pytest
from unittest.mock import MagicMock, patch
import uuid
from datetime import datetime

from shared.db.converters import (
    to_pydantic,
    to_sqlalchemy,
    paper_to_summary,
    paper_to_detail
)
from shared.models.schemas import (
    Paper,
    Author,
    Category,
    PaperSummary,
    PaperDetail,
    AuthorSummary,
    CategorySummary
)
from shared.db.models import (
    Paper as DBPaper,
    Author as DBAuthor,
    Category as DBCategory,
    PaperAuthor as DBPaperAuthor,
    PaperCategory as DBPaperCategory,
    ArxivSet as DBArxivSet
)

def test_paper_to_db_model():
    """Test converting Paper schema to DB model."""
    paper_id = uuid.uuid4()
    arxiv_id = "2101.12345"
    now = datetime.now()
    paper = Paper(
        paper_id=paper_id,
        arxiv_identifier=arxiv_id,
        title="Test Paper",
        abstract_preview="This is a test abstract",
        publication_date=now,
        full_abstract_s3_key="papers/abstracts/2101.12345.txt",
        created_at=now
    )
    
    db_paper = to_sqlalchemy(paper, DBPaper)
    
    assert isinstance(db_paper, DBPaper)
    assert db_paper.paper_id == paper_id
    assert db_paper.arxiv_identifier == arxiv_id
    assert db_paper.title == "Test Paper"
    assert db_paper.abstract_preview == "This is a test abstract"
    assert db_paper.created_at == now
    
def test_db_model_to_paper():
    """Test converting DB model to Paper schema."""
    paper_id = uuid.uuid4()
    arxiv_id = "2101.12345"
    now = datetime.now()
    db_paper = DBPaper(
        paper_id=paper_id,
        arxiv_identifier=arxiv_id,
        title="Test Paper",
        abstract_preview="This is a test abstract",
        publication_date=now,
        full_abstract_s3_key="papers/abstracts/2101.12345.txt",
        created_at=now
    )
    
    paper = to_pydantic(db_paper, Paper)
    
    assert isinstance(paper, Paper)
    assert paper.paper_id == paper_id
    assert paper.arxiv_identifier == arxiv_id
    assert paper.title == "Test Paper"
    assert paper.abstract_preview == "This is a test abstract"
    assert paper.created_at == now
    
def test_paper_to_summary():
    """Test converting DB Paper to PaperSummary."""
    paper_id = uuid.uuid4()
    arxiv_id = "2101.12345"
    now = datetime.now()
    
    # Create a DBPaper instance
    db_paper = DBPaper(
        paper_id=paper_id,
        arxiv_identifier=arxiv_id,
        title="Test Paper",
        abstract_preview="This is a test abstract",
        publication_date=now,
        full_abstract_s3_key="papers/abstracts/2101.12345.txt",
        created_at=now
    )
    
    # paper_categories will be accessed in the function, so we need to mock it
    db_paper.paper_categories = []
    
    # Test with primary_category parameter
    primary_category = "cs.AI"
    summary = paper_to_summary(db_paper, primary_category)
    
    assert isinstance(summary, PaperSummary)
    assert summary.paper_id == paper_id
    assert summary.arxiv_identifier == arxiv_id
    assert summary.title == "Test Paper"
    assert summary.abstract_preview == "This is a test abstract"
    assert summary.primary_category == primary_category
    assert summary.created_at == now

@patch('shared.db.converters.PaperDetail')
def test_paper_to_detail(mock_paper_detail):
    """Test converting DB Paper to PaperDetail using patch."""
    paper_id = uuid.uuid4()
    arxiv_id = "2101.12345"
    author_id = uuid.uuid4()
    category_id = uuid.uuid4()
    now = datetime.now()
    
    # Setup the PaperDetail mock return value
    mock_detail = MagicMock()
    mock_paper_detail.return_value = mock_detail
    
    # Create a mock paper with complete structure
    db_paper = MagicMock(spec=DBPaper)
    db_paper.paper_id = paper_id
    db_paper.arxiv_identifier = arxiv_id
    db_paper.title = "Test Paper"
    db_paper.abstract_preview = "This is a test abstract"
    db_paper.publication_date = now
    db_paper.full_abstract_s3_key = "papers/abstracts/2101.12345.txt"
    db_paper.created_at = now
    db_paper.updated_at = None
    
    # Create a mock author and paper_author
    author = MagicMock(spec=DBAuthor)
    author.author_id = author_id
    author.first_name = "John"
    author.last_name = "Doe"
    
    paper_author = MagicMock(spec=DBPaperAuthor)
    paper_author.author = author
    paper_author.author_position = 0
    
    # Create a mock category and paper_category
    arxiv_set = MagicMock(spec=DBArxivSet)
    arxiv_set.set_code = "cs"
    
    category = MagicMock(spec=DBCategory)
    category.category_id = category_id
    category.category_code = "cs.AI"
    category.category_name = "Artificial Intelligence"
    category.arxiv_set = arxiv_set
    
    paper_category = MagicMock(spec=DBPaperCategory)
    paper_category.category = category
    paper_category.is_primary = True
    
    # Set up relationships
    db_paper.paper_authors = [paper_author]
    db_paper.paper_categories = [paper_category]
    
    # Call the function
    result = paper_to_detail(db_paper)
    
    # Verify that the function was called correctly
    assert result == mock_detail  # The result should be our mock
    
    # Verify the PaperDetail constructor was called with correct args
    mock_paper_detail.assert_called_once()
    
    # We can check a few specific key arguments were passed
    call_kwargs = mock_paper_detail.call_args[1]
    assert call_kwargs['paper_id'] == paper_id
    assert call_kwargs['arxiv_identifier'] == arxiv_id
    assert call_kwargs['title'] == "Test Paper"
    assert call_kwargs['abstract_preview'] == "This is a test abstract"
    assert call_kwargs['created_at'] == now
    
    # Verify that authors and categories were processed
    assert len(call_kwargs['authors']) == 1
    assert len(call_kwargs['categories']) == 1
    assert call_kwargs['primary_category'] == "cs.AI" 