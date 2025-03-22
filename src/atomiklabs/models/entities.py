"""
Domain entity models for the ArXiv paper fetching system.

This module defines the supporting domain entities used throughout the system,
including Author, Category, and ArxivSet.
"""

class Author:
    """
    Represents an author of scientific papers.
    
    Responsible for encapsulating:
    - Author identification (name, ID)
    - Author metadata (affiliations, if available)
    """
    pass


class Category:
    """
    Represents an ArXiv category for papers.
    
    Responsible for encapsulating:
    - Category identification (code, name)
    - Category hierarchy information
    """
    pass


class ArxivSet:
    """
    Represents an ArXiv set of papers.
    
    Responsible for encapsulating:
    - Set identification (code, name)
    - Set metadata and criteria
    """
    pass 