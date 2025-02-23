import re
from datetime import datetime
from typing import Dict, List

def normalize_author_name(first_name: str, last_name: str) -> Dict[str, str]:
    """Normalize author names by removing extra spaces and standardizing case"""
    first = " ".join(first_name.strip().split())
    last = " ".join(last_name.strip().split())
    
    return {
        "first_name": first.title(),
        "last_name": last.title()
    }

def normalize_abstract(text: str) -> str:
    """Clean and normalize abstract text"""
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove LaTeX line breaks
    text = re.sub(r'\\n', ' ', text)
    # Clean up common LaTeX artifacts
    text = re.sub(r'\\[a-zA-Z]+{([^}]*)}', r'\1', text)
    return text.strip()

def normalize_categories(categories: List[str], category_map: Dict[str, str]) -> List[str]:
    """Normalize category codes using the mapping"""
    return [category_map.get(cat, cat) for cat in categories if cat] 