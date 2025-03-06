import pytest
from unittest.mock import MagicMock, patch
from shared.db.operations import (
    get_item_by_id,
    get_items,
    create_item,
    update_item,
    delete_item
)
from shared.db.models import Paper as DBPaper
from shared.models.schemas import Paper
import uuid
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

@pytest.fixture
def mock_session():
    """Fixture to provide a mock SQLAlchemy session."""
    session = MagicMock()
    return session

def test_get_item_by_id(mock_session):
    """Test retrieving an item by ID."""
    paper_id = uuid.uuid4()
    mock_paper = DBPaper(
        paper_id=paper_id,
        arxiv_identifier="2101.12345",
        title="Test Paper",
        abstract_preview="This is a test abstract",
        publication_date=datetime.now(),
        full_abstract_s3_key="papers/abstracts/2101.12345.txt"
    )
    
    # Configure mock session
    mock_session.query.return_value.filter.return_value.first.return_value = mock_paper
    
    # Add get_id_column method to DBPaper
    DBPaper.get_id_column = MagicMock(return_value=DBPaper.paper_id)
    
    # Call the function
    result = get_item_by_id(DBPaper, paper_id, session=mock_session)
    
    # Verify mock was called correctly
    mock_session.query.assert_called_once_with(DBPaper)
    
    # Verify result
    assert result == mock_paper
    
def test_get_item_by_id_with_default_session():
    """Test retrieving an item by ID using the default session."""
    paper_id = uuid.uuid4()
    mock_paper = DBPaper(
        paper_id=paper_id,
        arxiv_identifier="2101.12345",
        title="Test Paper",
        abstract_preview="This is a test abstract",
        publication_date=datetime.now(),
        full_abstract_s3_key="papers/abstracts/2101.12345.txt"
    )
    
    # Mock the db_session context manager
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_paper
    
    # Add get_id_column method to DBPaper
    DBPaper.get_id_column = MagicMock(return_value=DBPaper.paper_id)
    
    # Call the function with the default session
    with patch('shared.db.operations.db_session', return_value=MagicMock(__enter__=lambda x: mock_db, __exit__=lambda x, y, z, a: None)):
        result = get_item_by_id(DBPaper, paper_id)
    
    # Verify mock was called correctly
    mock_db.query.assert_called_once_with(DBPaper)
    
    # Verify result
    assert result == mock_paper

def test_get_item_by_id_exception(mock_session):
    """Test exception handling when retrieving an item by ID."""
    paper_id = uuid.uuid4()
    
    # Configure mock session to raise an exception
    mock_session.query.side_effect = SQLAlchemyError("Test error")
    
    # Add get_id_column method to DBPaper
    DBPaper.get_id_column = MagicMock(return_value=DBPaper.paper_id)
    
    # Call the function and expect an exception
    with pytest.raises(SQLAlchemyError):
        get_item_by_id(DBPaper, paper_id, session=mock_session)
    
def test_get_item_by_id_not_found(mock_session):
    """Test retrieving an item by ID when not found."""
    paper_id = uuid.uuid4()
    
    # Configure mock session
    mock_session.query.return_value.filter.return_value.first.return_value = None
    
    # Add get_id_column method to DBPaper
    DBPaper.get_id_column = MagicMock(return_value=DBPaper.paper_id)
    
    # Call the function
    result = get_item_by_id(DBPaper, paper_id, session=mock_session)
    
    # Verify result
    assert result is None
    
def test_get_items(mock_session):
    """Test retrieving items with pagination."""
    mock_papers = [
        DBPaper(
            paper_id=uuid.uuid4(),
            arxiv_identifier=f"2101.{i}",
            title=f"Test Paper {i}",
            abstract_preview=f"Abstract {i}",
            publication_date=datetime.now(),
            full_abstract_s3_key=f"papers/abstracts/2101.{i}.txt"
        )
        for i in range(3)
    ]
    
    # Configure mock session
    mock_query = mock_session.query.return_value
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = mock_papers
    mock_session.query.return_value.count.return_value = 3
    
    # Call the function with the correct parameters
    result = get_items(
        DBPaper, 
        page=1, 
        page_size=10,
        sort_by="publication_date",
        sort_desc=True, 
        session=mock_session,
        filters={"title": "Test Paper"}
    )
    
    # Verify mock was called correctly
    mock_session.query.assert_called_with(DBPaper)
    
    # Verify the result structure matches what's returned by get_items
    assert isinstance(result, dict)
    assert "items" in result
    assert "total" in result
    assert "page" in result
    assert "page_size" in result
    assert "pages" in result
    assert result["items"] == mock_papers
    assert result["total"] == 3
    assert result["page"] == 1
    assert result["page_size"] == 10

def test_get_items_with_default_session():
    """Test retrieving items with pagination using the default session."""
    mock_papers = [
        DBPaper(
            paper_id=uuid.uuid4(),
            arxiv_identifier=f"2101.{i}",
            title=f"Test Paper {i}",
            abstract_preview=f"Abstract {i}",
            publication_date=datetime.now(),
            full_abstract_s3_key=f"papers/abstracts/2101.{i}.txt"
        )
        for i in range(3)
    ]
    
    # Configure mock session
    mock_db = MagicMock()
    mock_query = mock_db.query.return_value
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = mock_papers
    mock_db.query.return_value.count.return_value = 3
    
    # Call the function with the default session
    with patch('shared.db.operations.db_session', return_value=MagicMock(__enter__=lambda x: mock_db, __exit__=lambda x, y, z, a: None)):
        result = get_items(
            DBPaper, 
            page=1, 
            page_size=10,
            sort_by="publication_date",
            sort_desc=True,
            filters={"title": "Test Paper"}
        )
    
    # Verify mock was called correctly
    mock_db.query.assert_called_with(DBPaper)
    
    # Verify the result structure
    assert isinstance(result, dict)
    assert result["items"] == mock_papers
    assert result["total"] == 3

def test_get_items_exception(mock_session):
    """Test exception handling when retrieving items."""
    # Configure mock session to raise an exception
    mock_session.query.side_effect = SQLAlchemyError("Test error")
    
    # Call the function and expect an exception
    with pytest.raises(SQLAlchemyError):
        get_items(DBPaper, session=mock_session)

def test_create_item(mock_session):
    """Test creating a new item."""
    paper_id = uuid.uuid4()
    paper_data = {
        "paper_id": paper_id,
        "arxiv_identifier": "2101.12345",
        "title": "Test Paper",
        "abstract_preview": "This is a test abstract",
        "publication_date": datetime.now(),
        "full_abstract_s3_key": "papers/abstracts/2101.12345.txt"
    }
    
    # Call the function with the actual DBPaper class
    result = create_item(DBPaper, paper_data, session=mock_session)
    
    # Verify mock was called correctly
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()
    
    # Verify the result is an instance of DBPaper with the correct attributes
    assert isinstance(result, DBPaper)
    assert result.paper_id == paper_id
    assert result.arxiv_identifier == paper_data["arxiv_identifier"]
    assert result.title == paper_data["title"]
    assert result.abstract_preview == paper_data["abstract_preview"]
    
def test_create_item_with_default_session():
    """Test creating a new item using the default session."""
    paper_id = uuid.uuid4()
    paper_data = {
        "paper_id": paper_id,
        "arxiv_identifier": "2101.12345",
        "title": "Test Paper",
        "abstract_preview": "This is a test abstract",
        "publication_date": datetime.now(),
        "full_abstract_s3_key": "papers/abstracts/2101.12345.txt"
    }
    
    # Configure mock session
    mock_db = MagicMock()
    
    # Call the function with the default session
    with patch('shared.db.operations.db_session', return_value=MagicMock(__enter__=lambda x: mock_db, __exit__=lambda x, y, z, a: None)):
        result = create_item(DBPaper, paper_data)
    
    # Verify mock was called correctly
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()
    mock_db.commit.assert_called_once()
    
    # Verify the result is an instance of DBPaper
    assert isinstance(result, DBPaper)

def test_create_item_exception(mock_session):
    """Test exception handling when creating an item."""
    paper_data = {
        "paper_id": uuid.uuid4(),
        "arxiv_identifier": "2101.12345",
        "title": "Test Paper",
        "abstract_preview": "This is a test abstract",
        "publication_date": datetime.now(),
        "full_abstract_s3_key": "papers/abstracts/2101.12345.txt"
    }
    
    # Configure mock session to raise an exception
    mock_session.add.side_effect = SQLAlchemyError("Test error")
    
    # Call the function and expect an exception
    with pytest.raises(SQLAlchemyError):
        create_item(DBPaper, paper_data, session=mock_session)
    
def test_update_item(mock_session):
    """Test updating an existing item."""
    paper_id = uuid.uuid4()
    existing_paper = DBPaper(
        paper_id=paper_id,
        arxiv_identifier="2101.12345",
        title="Old Title",
        abstract_preview="Old Abstract",
        publication_date=datetime.now(),
        full_abstract_s3_key="papers/abstracts/2101.12345.txt"
    )
    
    # Configure mock session
    mock_session.query.return_value.filter.return_value.first.return_value = existing_paper
    
    # Add get_id_column method to DBPaper
    DBPaper.get_id_column = MagicMock(return_value=DBPaper.paper_id)
    
    # Create updated paper data
    updated_data = {
        "title": "New Title",
        "abstract_preview": "New Abstract"
    }
    
    # Call the function
    result = update_item(DBPaper, paper_id, updated_data, session=mock_session)
    
    # Verify mock was called correctly
    mock_session.query.assert_called_with(DBPaper)
    mock_session.flush.assert_called_once()
    
    # Verify result
    assert result == existing_paper
    assert existing_paper.title == "New Title"
    assert existing_paper.abstract_preview == "New Abstract"
    
def test_update_item_with_default_session():
    """Test updating an existing item using the default session."""
    paper_id = uuid.uuid4()
    existing_paper = DBPaper(
        paper_id=paper_id,
        arxiv_identifier="2101.12345",
        title="Old Title",
        abstract_preview="Old Abstract",
        publication_date=datetime.now(),
        full_abstract_s3_key="papers/abstracts/2101.12345.txt"
    )
    
    # Configure mock session
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = existing_paper
    
    # Add get_id_column method to DBPaper
    DBPaper.get_id_column = MagicMock(return_value=DBPaper.paper_id)
    
    # Create updated paper data
    updated_data = {
        "title": "New Title",
        "abstract_preview": "New Abstract"
    }
    
    # Call the function with the default session
    with patch('shared.db.operations.db_session', return_value=MagicMock(__enter__=lambda x: mock_db, __exit__=lambda x, y, z, a: None)):
        result = update_item(DBPaper, paper_id, updated_data)
    
    # Verify mock was called correctly
    mock_db.query.assert_called_with(DBPaper)
    mock_db.commit.assert_called_once()
    
    # Verify result
    assert result == existing_paper

def test_update_item_exception(mock_session):
    """Test exception handling when updating an item."""
    paper_id = uuid.uuid4()
    
    # Configure mock session to raise an exception
    mock_session.query.side_effect = SQLAlchemyError("Test error")
    
    # Add get_id_column method to DBPaper
    DBPaper.get_id_column = MagicMock(return_value=DBPaper.paper_id)
    
    # Call the function and expect an exception
    with pytest.raises(SQLAlchemyError):
        update_item(DBPaper, paper_id, {"title": "New Title"}, session=mock_session)
    
def test_delete_item(mock_session):
    """Test deleting an item."""
    paper_id = uuid.uuid4()
    existing_paper = DBPaper(
        paper_id=paper_id,
        arxiv_identifier="2101.12345",
        title="Test Paper",
        abstract_preview="This is a test abstract",
        publication_date=datetime.now(),
        full_abstract_s3_key="papers/abstracts/2101.12345.txt"
    )
    
    # Configure mock session
    mock_session.query.return_value.filter.return_value.first.return_value = existing_paper
    
    # Add get_id_column method to DBPaper
    DBPaper.get_id_column = MagicMock(return_value=DBPaper.paper_id)
    
    # Call the function
    result = delete_item(DBPaper, paper_id, session=mock_session)
    
    # Verify mock was called correctly
    mock_session.query.assert_called_with(DBPaper)
    mock_session.delete.assert_called_once_with(existing_paper)
    mock_session.flush.assert_called_once()  # flush, not commit
    
    # Verify result
    assert result is True

def test_delete_item_with_default_session():
    """Test deleting an item using the default session."""
    paper_id = uuid.uuid4()
    existing_paper = DBPaper(
        paper_id=paper_id,
        arxiv_identifier="2101.12345",
        title="Test Paper",
        abstract_preview="This is a test abstract",
        publication_date=datetime.now(),
        full_abstract_s3_key="papers/abstracts/2101.12345.txt"
    )
    
    # Configure mock session
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = existing_paper
    
    # Add get_id_column method to DBPaper
    DBPaper.get_id_column = MagicMock(return_value=DBPaper.paper_id)
    
    # Call the function with the default session
    with patch('shared.db.operations.db_session', return_value=MagicMock(__enter__=lambda x: mock_db, __exit__=lambda x, y, z, a: None)):
        result = delete_item(DBPaper, paper_id)
    
    # Verify mock was called correctly
    mock_db.query.assert_called_with(DBPaper)
    mock_db.delete.assert_called_once_with(existing_paper)
    mock_db.commit.assert_called_once()
    
    # Verify result
    assert result is True

def test_delete_item_exception(mock_session):
    """Test exception handling when deleting an item."""
    paper_id = uuid.uuid4()
    
    # Configure mock session to raise an exception
    mock_session.query.side_effect = SQLAlchemyError("Test error")
    
    # Add get_id_column method to DBPaper
    DBPaper.get_id_column = MagicMock(return_value=DBPaper.paper_id)
    
    # Call the function and expect an exception
    with pytest.raises(SQLAlchemyError):
        delete_item(DBPaper, paper_id, session=mock_session)
    
def test_delete_item_not_found(mock_session):
    """Test deleting an item that doesn't exist."""
    paper_id = uuid.uuid4()
    
    # Configure mock session
    mock_session.query.return_value.filter.return_value.first.return_value = None
    
    # Add get_id_column method to DBPaper
    DBPaper.get_id_column = MagicMock(return_value=DBPaper.paper_id)
    
    # Call the function
    result = delete_item(DBPaper, paper_id, session=mock_session)
    
    # Verify mock was not called for delete
    mock_session.delete.assert_not_called()
    
    # Verify result
    assert result is False 