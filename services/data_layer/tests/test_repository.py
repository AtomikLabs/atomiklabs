"""
Unit tests for the repository implementations in the data layer.
"""
import datetime
from unittest.mock import patch, MagicMock, call

import pytest
from sqlalchemy.exc import SQLAlchemyError

# We need to mock these before we import the repositories
Article = MagicMock()
Author = MagicMock()
Category = MagicMock()
ProcessingEvent = MagicMock()
Newsletter = MagicMock()
Email = MagicMock()

# Apply patches to models
@pytest.fixture(autouse=True)
def patch_models():
    with patch('src.repository.Article', Article), \
         patch('src.repository.Author', Author), \
         patch('src.repository.Category', Category), \
         patch('src.repository.ProcessingEvent', ProcessingEvent), \
         patch('src.repository.Newsletter', Newsletter), \
         patch('src.repository.Email', Email):
        yield

from src.repository import (
    ArticleRepository, 
    AuthorRepository,
    CategoryRepository,
    OrganizationRepository,
    ProcessingEventRepository,
    NewsletterRepository,
    EmailRepository
)

class TestArticleRepository:
    """Unit tests for ArticleRepository."""

    def test_create_article_success(self):
        """Test creating an article successfully."""
        # Arrange
        mock_session = MagicMock()
        article_data = {
            "source_id": "test123",
            "source": "arxiv",
            "title": "Test Article",
            "publication_date": datetime.date.today(),
            "abstract_text": "This is a test abstract"
        }
        mock_article = MagicMock()
        
        # Configure the Article mock to return our mock_article
        Article.return_value = mock_article
        
        # Act
        article = ArticleRepository.create_article(
            session=mock_session,
            **article_data
        )
        
        # Assert
        assert article is mock_article
        # Don't check exact parameters since the implementation may add defaults
        assert Article.call_count == 1
        # Just verify the article was created with our data (included in the call)
        for key, value in article_data.items():
            assert Article.call_args.kwargs[key] == value
        mock_session.add.assert_called_once_with(mock_article)
        mock_session.commit.assert_called_once()

    def test_create_article_error(self):
        """Test handling errors when creating an article."""
        # Arrange
        mock_session = MagicMock()
        mock_session.commit.side_effect = SQLAlchemyError("Test error")
        Article.return_value = MagicMock()
        
        # Act/Assert
        with pytest.raises(SQLAlchemyError):
            ArticleRepository.create_article(
                session=mock_session,
                source_id="test123",
                source="arxiv",
                title="Test Article",
                publication_date=datetime.date.today()
            )
        
        mock_session.rollback.assert_called_once()

    def test_get_article(self):
        """Test getting an article by ID."""
        # Arrange
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = "test_article"
        
        # Act
        article = ArticleRepository.get_article(mock_session, 1)
        
        # Assert
        assert article == "test_article"
        mock_session.query.assert_called_once()
        mock_query.filter.assert_called_once()
        mock_query.first.assert_called_once()

    def test_get_article_by_source_id(self):
        """Test getting an article by source and source_id."""
        # Arrange
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = "test_article"
        
        # Act
        article = ArticleRepository.get_article_by_source_id(
            mock_session, "arxiv", "2301.12345"
        )
        
        # Assert
        assert article == "test_article"
        mock_session.query.assert_called_once()
        mock_query.filter.assert_called_once()
        mock_query.first.assert_called_once()


class TestAuthorRepository:
    """Unit tests for AuthorRepository."""

    def test_create_author_new(self):
        """Test creating a new author."""
        # Arrange
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        # Return None to simulate author not found
        mock_query.first.return_value = None
        
        # Create a mock author to return from Author()
        mock_author = MagicMock()
        Author.return_value = mock_author
        
        # Act
        author = AuthorRepository.create_author(
            session=mock_session,
            name="Test Author",
            email="test@example.com"
        )
        
        # Assert
        assert author is mock_author
        Author.assert_called_once_with(name="Test Author", email="test@example.com")
        mock_session.add.assert_called_once_with(mock_author)
        mock_session.commit.assert_called_once()

    def test_create_author_existing(self):
        """Test creating an author that already exists."""
        # Arrange
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # Return an existing author
        existing_author = MagicMock()
        existing_author.name = "Test Author"
        existing_author.email = None
        mock_query.first.return_value = existing_author
        
        # Act
        author = AuthorRepository.create_author(
            session=mock_session,
            name="Test Author",
            email="new@example.com"
        )
        
        # Assert
        assert author is existing_author
        assert author.email == "new@example.com"  # Email should be updated
        mock_session.add.assert_not_called()  # No new author added
        mock_session.commit.assert_called_once()  # Commit the email update

    def test_get_author(self):
        """Test getting an author by ID."""
        # Arrange
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = "test_author"
        
        # Act
        author = AuthorRepository.get_author(mock_session, 1)
        
        # Assert
        assert author == "test_author"
        mock_session.query.assert_called_once()
        mock_query.filter.assert_called_once()
        mock_query.first.assert_called_once()


class TestCategoryRepository:
    """Unit tests for CategoryRepository."""

    def test_create_category_new(self):
        """Test creating a new category."""
        # Arrange
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        # Return None to simulate category not found
        mock_query.first.return_value = None
        
        # Create a mock category to return
        mock_category = MagicMock()
        Category.return_value = mock_category
        
        # Act
        category = CategoryRepository.create_category(
            session=mock_session,
            name="Test Category",
            code="TEST"
        )
        
        # Assert
        assert category is mock_category
        Category.assert_called_once_with(name="Test Category", code="TEST", parent_id=None)
        mock_session.add.assert_called_once_with(mock_category)
        mock_session.commit.assert_called_once()

    def test_create_category_existing(self):
        """Test creating a category that already exists."""
        # Arrange
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # Return an existing category
        existing_category = MagicMock()
        existing_category.code = "TEST"
        existing_category.name = "Old Name"
        mock_query.first.return_value = existing_category
        
        # Act
        category = CategoryRepository.create_category(
            session=mock_session,
            name="New Name",
            code="TEST"
        )
        
        # Assert
        assert category is existing_category
        assert category.name == "New Name"  # Name should be updated
        mock_session.add.assert_not_called()  # No new category added
        mock_session.commit.assert_called_once()  # Commit the name update

    def test_get_category_by_code(self):
        """Test getting a category by code."""
        # Arrange
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = "test_category"
        
        # Act
        category = CategoryRepository.get_category_by_code(mock_session, "TEST")
        
        # Assert
        assert category == "test_category"
        mock_session.query.assert_called_once()
        mock_query.filter.assert_called_once()
        mock_query.first.assert_called_once()


# Add more unit tests for other repository classes as needed 