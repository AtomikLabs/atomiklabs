from typing import Dict, Any, Union, List, Optional
from datetime import datetime, date
import re
import uuid
import logging
from .exceptions import Neo4jDataValidationError

logger = logging.getLogger(__name__)


def generate_uuid() -> str:
    """Generate a UUID string for use as node ID."""
    return str(uuid.uuid4())


def sanitize_cypher_string(value: str) -> str:
    """Escape special characters in strings for Cypher queries."""
    if not isinstance(value, str):
        return value
    return value.replace("'", "\\'").replace('"', '\\"')


def convert_to_neo4j_date(date_obj: Union[date, datetime, str]) -> str:
    """Convert Python date objects to Neo4j date format string.
    
    Args:
        date_obj: A date, datetime, or ISO format date string
    
    Returns:
        A string formatted for Neo4j date functions
    """
    if isinstance(date_obj, datetime):
        return f"datetime('{date_obj.isoformat()}')"
    elif isinstance(date_obj, date):
        return f"date('{date_obj.isoformat()}')"
    elif isinstance(date_obj, str):
        # Try to determine if it's a date or datetime string
        if "T" in date_obj or " " in date_obj:
            return f"datetime('{date_obj}')"
        else:
            return f"date('{date_obj}')"
    return None


def format_cypher_properties(properties: Dict[str, Any]) -> str:
    """Convert a Python dictionary to a Cypher properties string.
    
    Args:
        properties: Dictionary of property names and values
    
    Returns:
        A formatted string like "{key1: 'value1', key2: 42}"
    """
    formatted_props = []
    
    for key, value in properties.items():
        if value is None:
            continue
            
        if isinstance(value, str):
            # Escape strings and wrap in quotes
            formatted_value = f"'{sanitize_cypher_string(value)}'"
        elif isinstance(value, (int, float, bool)):
            # Use as-is for numeric and boolean values
            formatted_value = str(value).lower() if isinstance(value, bool) else str(value)
        elif isinstance(value, (date, datetime)):
            # Convert date objects
            formatted_value = convert_to_neo4j_date(value)
        elif isinstance(value, list):
            # Handle lists
            formatted_items = []
            for item in value:
                if isinstance(item, str):
                    formatted_items.append(f"'{sanitize_cypher_string(item)}'")
                elif isinstance(item, (int, float, bool)):
                    formatted_items.append(str(item).lower() if isinstance(item, bool) else str(item))
                else:
                    formatted_items.append("null")
            formatted_value = f"[{', '.join(formatted_items)}]"
        else:
            # Default to null for unsupported types
            formatted_value = "null"
        
        formatted_props.append(f"{key}: {formatted_value}")
    
    return "{" + ", ".join(formatted_props) + "}"


def validate_node_data(node_type: str, data: Dict[str, Any], required_fields: List[str]) -> None:
    """Validate that required fields are present in the node data.
    
    Args:
        node_type: String name of the node type for error messages
        data: Dictionary of node properties
        required_fields: List of required field names
        
    Raises:
        Neo4jDataValidationError: If validation fails
    """
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    
    if missing_fields:
        raise Neo4jDataValidationError(
            f"Missing required fields for {node_type}: {', '.join(missing_fields)}"
        )


def extract_id_from_uri(uri: str) -> Optional[str]:
    """Extract node ID from a Neo4j URI.
    
    Args:
        uri: Neo4j URI string (e.g., "neo4j://graph.db/node/123")
        
    Returns:
        Node ID as a string or None if not found
    """
    match = re.search(r'/node/(\d+)$', uri)
    if match:
        return match.group(1)
    return None
