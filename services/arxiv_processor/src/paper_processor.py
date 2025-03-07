#!/usr/bin/env python3
"""
Module for processing paper data into our schema models
"""

import logging
import uuid
from datetime import datetime, UTC
from typing import List, Dict, Any, Optional, Tuple

from shared.models.schemas import (
    Paper, Author, Category, PaperAuthor, PaperCategory,
    ArxivSet, AuthorAffiliation, Affiliation
)
from .arxiv_fetcher import latex_to_human_readable

logger = logging.getLogger(__name__)

def process_paper(paper_data: Dict[str, Any]) -> Tuple[Paper, List[Author], List[Category], List[PaperAuthor], List[PaperCategory]]:
    """
    Process a paper record into our schema models.
    
    Args:
        paper_data: Paper data from ArXiv
        
    Returns:
        Tuple containing:
        - Paper: The paper model
        - List[Author]: List of authors
        - List[Category]: List of categories
        - List[PaperAuthor]: List of paper-author relationships
        - List[PaperCategory]: List of paper-category relationships
    """
    # Process the abstract
    full_abstract = latex_to_human_readable(paper_data.get('abstract', ''))
    
    # Create a preview (first ~150 chars)
    abstract_preview = full_abstract[:147] + '...' if len(full_abstract) > 150 else full_abstract
    
    # Parse the publication date
    pub_date = None
    if 'publication_date' in paper_data:
        try:
            pub_date = datetime.fromisoformat(paper_data['publication_date'])
        except (ValueError, TypeError):
            logger.error(f"Invalid publication date format: {paper_data.get('publication_date')}")
            pub_date = datetime.now(UTC)
    else:
        pub_date = datetime.now(UTC)
    
    # Generate a paper ID
    paper_id = uuid.uuid4()
    
    # Create the Paper model
    paper = Paper(
        paper_id=paper_id,
        arxiv_identifier=paper_data.get('arxiv_id', paper_data.get('identifier', '')),
        title=paper_data.get('title', ''),
        abstract_preview=abstract_preview,
        publication_date=pub_date,
        created_at=datetime.now(UTC)
    )
    
    # Process authors
    authors = []
    paper_authors = []
    
    for idx, author_data in enumerate(paper_data.get('authors', [])):
        author_id = uuid.uuid4()
        author = Author(
            author_id=author_id,
            first_name=author_data.get('first_name', ''),
            last_name=author_data.get('last_name', ''),
            created_at=datetime.now(UTC)
        )
        authors.append(author)
        
        # Create the paper-author relationship
        paper_author = PaperAuthor(
            paper_author_id=uuid.uuid4(),
            paper_id=paper_id,
            author_id=author_id,
            author_position=idx,
            created_at=datetime.now(UTC)
        )
        paper_authors.append(paper_author)
    
    # Process categories
    categories = []
    paper_categories = []
    
    # We'll rely on the API to handle the set-category relationships
    # For now, we'll use a placeholder set_id
    set_id = uuid.uuid4()
    
    for idx, category_code in enumerate(paper_data.get('categories', [])):
        category_id = uuid.uuid4()
        
        # Create the category
        category = Category(
            category_id=category_id,
            set_id=set_id,  # This will be properly set by the API
            category_code=category_code,
            category_name=f"Computer Science - {category_code}",  # Simplified for now
            created_at=datetime.now(UTC)
        )
        categories.append(category)
        
        # Create the paper-category relationship
        is_primary = idx == 0 or category_code == paper_data.get('primary_category', '')
        paper_category = PaperCategory(
            paper_category_id=uuid.uuid4(),
            paper_id=paper_id,
            category_id=category_id,
            is_primary=is_primary,
            created_at=datetime.now(UTC)
        )
        paper_categories.append(paper_category)
    
    return paper, authors, categories, paper_authors, paper_categories


def process_papers(papers_data: List[Dict[str, Any]]) -> Dict[str, List]:
    """
    Process a list of paper records into our schema models.
    
    Args:
        papers_data: List of paper data from ArXiv
        
    Returns:
        Dictionary containing:
        - papers: List of Paper models
        - authors: List of Author models
        - categories: List of Category models
        - paper_authors: List of PaperAuthor models
        - paper_categories: List of PaperCategory models
        - abstracts: List of dictionaries containing paper_id and abstract text
    """
    processed_data = {
        "papers": [],
        "authors": [],
        "categories": [],
        "paper_authors": [],
        "paper_categories": [],
        "abstracts": []
    }
    
    for paper_data in papers_data:
        try:
            # Process the paper
            paper, authors, categories, paper_authors, paper_categories = process_paper(paper_data)
            
            # Add to the result lists
            processed_data["papers"].append(paper)
            processed_data["authors"].extend(authors)
            processed_data["categories"].extend(categories)
            processed_data["paper_authors"].extend(paper_authors)
            processed_data["paper_categories"].extend(paper_categories)
            
            # Add the abstract
            abstract_text = latex_to_human_readable(paper_data.get('abstract', ''))
            processed_data["abstracts"].append({
                "paper_id": str(paper.paper_id),
                "abstract": abstract_text
            })
            
        except Exception as e:
            logger.error(f"Error processing paper: {e}")
            logger.error(f"Paper data: {paper_data}")
            continue
    
    logger.info(f"Processed {len(processed_data['papers'])} papers")
    logger.info(f"Processed {len(processed_data['authors'])} authors")
    logger.info(f"Processed {len(processed_data['categories'])} categories")
    
    return processed_data 