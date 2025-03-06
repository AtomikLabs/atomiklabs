import pytest
from models.schemas import (
    Paper,
    Author,
    Category,
    ErrorResponse,
    PaperSummary,
    PaperDetail,
    PaginatedPapers
)
import uuid
from datetime import datetime
from uuid import UUID

def test_paper_model_validation():
    """Test Paper model validation."""
    # Test valid paper creation
    paper_id = uuid.uuid4()
    arxiv_id = "2101.12345"
    paper = Paper(
        paper_id=paper_id,
        arxiv_identifier=arxiv_id,
        title="Test Paper",
        abstract_preview="This is a test abstract",
        publication_date=datetime.now(),
        full_abstract_s3_key="papers/abstracts/2101.12345.txt",
    )
    
    assert paper.paper_id == paper_id
    assert paper.title == "Test Paper"
    assert paper.abstract_preview == "This is a test abstract"
    
    # Test paper serialization
    paper_dict = paper.model_dump()
    assert isinstance(paper_dict, dict)
    assert paper_dict["paper_id"] == paper_id
    assert paper_dict["title"] == "Test Paper"
    
def test_author_model():
    """Test Author model."""
    author_id = uuid.uuid4()
    author = Author(
        author_id=author_id,
        first_name="John",
        last_name="Doe"
    )
    assert author.first_name == "John"
    assert author.last_name == "Doe"
    
    author_dict = author.model_dump()
    assert isinstance(author_dict, dict)
    assert author_dict["first_name"] == "John"
    assert author_dict["last_name"] == "Doe"
    
def test_category_model():
    """Test Category model."""
    category_id = uuid.uuid4()
    set_id = uuid.uuid4()
    category = Category(
        category_id=category_id,
        set_id=set_id,
        category_code="cs.AI",
        category_name="Artificial Intelligence"
    )
    assert category.category_id == category_id
    assert category.category_code == "cs.AI"
    assert category.category_name == "Artificial Intelligence"
    
    category_dict = category.model_dump()
    assert isinstance(category_dict, dict)
    assert category_dict["category_code"] == "cs.AI"
    assert category_dict["category_name"] == "Artificial Intelligence"
    
def test_error_response():
    """Test ErrorResponse model."""
    error_response = ErrorResponse(
        error="not_found",
        details={"message": "Resource not found"}
    )
    
    assert error_response.error == "not_found"
    assert error_response.details["message"] == "Resource not found"
    
    response_dict = error_response.model_dump()
    assert isinstance(response_dict, dict)
    assert response_dict["error"] == "not_found"
    
def test_paginated_papers():
    """Test PaginatedPapers model."""
    papers = [
        PaperSummary(
            paper_id=uuid.uuid4(),
            arxiv_identifier=f"2101.{i}",
            title=f"Test Paper {i}",
            abstract_preview=f"Abstract {i}",
            publication_date=datetime.now(),
            primary_category="cs.AI",
            created_at=datetime.now()
        )
        for i in range(3)
    ]
    
    paginated = PaginatedPapers(
        items=papers,
        total=3,
        page=1,
        page_size=10,
        pages=1
    )
    
    assert len(paginated.items) == 3
    assert paginated.total == 3
    assert paginated.page == 1
    assert paginated.page_size == 10
    assert paginated.pages == 1 