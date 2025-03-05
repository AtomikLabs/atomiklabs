"""
Mock implementations of shared modules for testing
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from unittest.mock import MagicMock

# Mock the shared models/schemas
class ValidationError(Exception):
    """Mock validation error class"""
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors or []


class BaseModel:
    """Mock base model class"""
    def __init__(self, **kwargs):
        """Initialize with keyword arguments"""
        for key, value in kwargs.items():
            setattr(self, key, value)
            
    def dict(self):
        """Return all attributes as a dict"""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        
    def from_orm(self, obj):
        """Mock from_orm method"""
        if hasattr(obj, 'dict'):
            for key, value in obj.dict().items():
                setattr(self, key, value)
        return self
        
    @classmethod
    def from_orm(cls, obj):
        """Class method for from_orm"""
        instance = cls()
        if hasattr(obj, 'dict'):
            for key, value in obj.dict().items():
                setattr(instance, key, value)
        return instance


class Paper(BaseModel):
    """Mock Paper model"""
    paper_id: str = ""
    arxiv_identifier: str = ""
    title: str = ""
    abstract: str = ""
    primary_category: str = ""
    submission_date: datetime = None
    update_date: datetime = None


class PaperDetail(Paper):
    """Mock PaperDetail model"""
    authors: List[Dict[str, Any]] = []
    categories: List[str] = []


class Author(BaseModel):
    """Mock Author model"""
    author_id: str = ""
    first_name: str = ""
    last_name: str = ""


class Category(BaseModel):
    """Mock Category model"""
    category_code: str = ""
    name: str = ""
    description: str = ""


class ArxivSet(BaseModel):
    """Mock ArxivSet model"""
    set_id: str = ""
    set_code: str = ""
    name: str = ""
    description: str = ""


class PaperSearchRequest(BaseModel):
    """Mock PaperSearchRequest model"""
    page: int = 1
    page_size: int = 20
    category: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search_term: Optional[str] = None


class PaginatedResponse(BaseModel):
    """Mock PaginatedResponse model"""
    items: List[Any] = []
    page: int = 1
    page_size: int = 20
    total_pages: int = 1
    total_items: int = 0
    
    def __class_getitem__(cls, item):
        """Support for subscripting (e.g., PaginatedResponse[Paper])"""
        return cls


class ErrorResponse(BaseModel):
    """Mock ErrorResponse model"""
    error: str = ""
    details: Any = None
    error_code: Optional[str] = None
    message: Optional[str] = None
    
    def __init__(self, **kwargs):
        # Handle old-style initialization
        if 'error_code' in kwargs and 'error' not in kwargs:
            kwargs['error'] = kwargs['error_code']
            
        if 'message' in kwargs and kwargs['message'] is not None:
            if 'details' not in kwargs or kwargs['details'] is None:
                kwargs['details'] = {}
                
            if isinstance(kwargs['details'], dict):
                kwargs['details']['message'] = kwargs['message']
            else:
                # If details is already something else, convert to dict
                kwargs['details'] = {
                    'message': kwargs['message'],
                    'info': kwargs['details']
                }
                
        # Remove old-style keys to avoid conflicts
        kwargs.pop('error_code', None)
        kwargs.pop('message', None)
            
        super().__init__(**kwargs)
        
    def dict(self):
        """Compatibility method for dict()"""
        return self.model_dump()
    
    def model_dump(self):
        """Return data as dict, ensuring error and details are present"""
        data = {
            "error": self.error,
            "details": self.details
        }
        return data


class APIResponse(BaseModel):
    """Mock APIResponse model"""
    status: str = "success"
    data: Any = None


# Mock the shared db access functions
def get_db_connection():
    """Mock database connection"""
    connection = MagicMock()
    connection.__enter__ = MagicMock(return_value=connection)
    connection.__exit__ = MagicMock(return_value=None)
    return connection


def get_paper_by_id(conn, paper_id):
    """Mock get_paper_by_id function"""
    paper = Paper()
    paper.paper_id = paper_id
    paper.arxiv_identifier = "2404.12345"
    paper.title = "Test Paper"
    paper.abstract = "Test abstract"
    paper.primary_category = "CS"
    return paper


def search_papers(conn, search_term=None, category=None, date_from=None, date_to=None, limit=20, offset=0):
    """Mock search_papers function"""
    papers = [Paper() for _ in range(3)]
    return papers, 3


def get_papers_by_category(conn, category, date_from=None, date_to=None, limit=20, offset=0):
    """Mock get_papers_by_category function"""
    papers = [Paper() for _ in range(2)]
    return papers, 2


def get_papers_by_date_range(conn, date_from=None, date_to=None, limit=20, offset=0):
    """Mock get_papers_by_date_range function"""
    papers = [Paper() for _ in range(4)]
    return papers, 4


def get_author_by_id(conn, author_id):
    """Mock get_author_by_id function"""
    author = Author()
    author.author_id = author_id
    author.first_name = "Jane"
    author.last_name = "Doe"
    return author


def search_authors(conn, search_term=None, limit=20, offset=0):
    """Mock search_authors function"""
    authors = [Author() for _ in range(3)]
    return authors, 3


def get_authors_by_paper(conn, paper_id):
    """Mock get_authors_by_paper function"""
    authors = [Author() for _ in range(2)]
    return authors


def get_all_categories(conn):
    """Mock get_all_categories function"""
    categories = [Category() for _ in range(5)]
    return categories


def get_category_by_code(conn, code):
    """Mock get_category_by_code function"""
    category = Category()
    category.category_code = code
    category.name = "Test Category"
    return category


def get_all_sets(conn):
    """Mock get_all_sets function"""
    sets = [ArxivSet() for _ in range(3)]
    return sets


def get_set_by_code(conn, code):
    """Mock get_set_by_code function"""
    arxiv_set = ArxivSet()
    arxiv_set.set_code = code
    arxiv_set.name = "Test Set"
    return arxiv_set


def get_set_by_id(conn, set_id):
    """Mock get_set_by_id function"""
    arxiv_set = ArxivSet()
    arxiv_set.set_id = set_id
    arxiv_set.set_code = "cs"
    arxiv_set.name = "Computer Science"
    return arxiv_set 