"""
Unit tests for the repository implementations in the data layer.
"""

import datetime
import os
import sys
from unittest.mock import MagicMock, call, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock the models first
with (
    patch("src.models.Article", MagicMock()),
    patch("src.models.Author", MagicMock()),
    patch("src.models.Category", MagicMock()),
    patch("src.models.ProcessingEvent", MagicMock()),
    patch("src.models.Newsletter", MagicMock()),
    patch("src.models.Email", MagicMock()),
):

    # Import repositories after patching models
    from src.repository import (
        ArticleRepository,
        AuthorRepository,
        CategoryRepository,
        EmailRepository,
        NewsletterRepository,
        OrganizationRepository,
        ProcessingEventRepository,
    )


# Mock classes for all models used in repositories
@pytest.fixture
def mock_models():
    with (
        patch("src.repository.Article") as mock_article,
        patch("src.repository.Author") as mock_author,
        patch("src.repository.Category") as mock_category,
        patch("src.repository.ProcessingEvent") as mock_processing_event,
        patch("src.repository.Newsletter") as mock_newsletter,
        patch("src.repository.Email") as mock_email,
    ):

        yield {
            "Article": mock_article,
            "Author": mock_author,
            "Category": mock_category,
            "ProcessingEvent": mock_processing_event,
            "Newsletter": mock_newsletter,
            "Email": mock_email,
        }


class TestArticleRepository:
    """Unit tests for ArticleRepository."""

    def test_create_article_success(self, mock_models):
        """Test creating an article successfully."""
        # Arrange
        mock_session = MagicMock()
        article_data = {
            "source_id": "test123",
            "source": "arxiv",
            "title": "Test Article",
            "publication_date": datetime.date.today(),
            "abstract_text": "This is a test abstract",
        }
        mock_article = MagicMock()

        # Configure the Article mock to return our mock_article
        mock_models["Article"].return_value = mock_article

        # Act
        article = ArticleRepository.create_article(session=mock_session, **article_data)

        # Assert
        assert article is mock_article
        # Don't check exact parameters since the implementation may add defaults
        assert mock_models["Article"].call_count == 1
        # Just verify the article was created with our data (included in the call)
        for key, value in article_data.items():
            assert mock_models["Article"].call_args.kwargs[key] == value
        mock_session.add.assert_called_once_with(mock_article)
        mock_session.commit.assert_called_once()

    def test_create_article_error(self, mock_models):
        """Test handling errors when creating an article."""
        # Arrange
        mock_session = MagicMock()
        mock_session.commit.side_effect = SQLAlchemyError("Test error")
        mock_models["Article"].return_value = MagicMock()

        # Act/Assert
        with pytest.raises(SQLAlchemyError):
            ArticleRepository.create_article(
                session=mock_session,
                source_id="test123",
                source="arxiv",
                title="Test Article",
                publication_date=datetime.date.today(),
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
        article = ArticleRepository.get_article_by_source_id(mock_session, "arxiv", "2301.12345")

        # Assert
        assert article == "test_article"
        mock_session.query.assert_called_once()
        mock_query.filter.assert_called_once()
        mock_query.first.assert_called_once()


class TestAuthorRepository:
    """Unit tests for AuthorRepository."""

    def test_create_author_new(self, mock_models):
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
        mock_models["Author"].return_value = mock_author

        # Act
        author = AuthorRepository.create_author(session=mock_session, name="Test Author", email="test@example.com")

        # Assert
        assert author is mock_author
        mock_models["Author"].assert_called_once_with(name="Test Author", email="test@example.com")
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
        author = AuthorRepository.create_author(session=mock_session, name="Test Author", email="new@example.com")

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

    def test_create_category_new(self, mock_models):
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
        mock_models["Category"].return_value = mock_category

        # Act
        category = CategoryRepository.create_category(session=mock_session, name="Test Category", code="TEST")

        # Assert
        assert category is mock_category
        mock_models["Category"].assert_called_once_with(name="Test Category", code="TEST", parent_id=None)
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
        category = CategoryRepository.create_category(session=mock_session, name="New Name", code="TEST")

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
