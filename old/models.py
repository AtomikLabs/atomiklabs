from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from .utils import format_cypher_properties, validate_node_data


@dataclass
class Neo4jNode:
    """Base class for all Neo4j nodes."""
    id: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_cypher_create(self) -> str:
        """Convert node to Cypher CREATE statement."""
        labels_str = ":".join(self.labels)
        props_str = format_cypher_properties(self.properties)
        return f"CREATE (n:{labels_str} {props_str})"
    
    def to_cypher_merge(self) -> str:
        """Convert node to Cypher MERGE statement using ID."""
        if not self.id:
            raise ValueError("Cannot generate MERGE statement without an ID")
        
        labels_str = ":".join(self.labels)
        props_str = format_cypher_properties(self.properties)
        return f"MERGE (n:{labels_str} {{id: '{self.id}'}}) SET n = {props_str}"
    
    @classmethod
    def from_neo4j_result(cls, record: Dict[str, Any]):
        """Create instance from Neo4j query result."""
        raise NotImplementedError("Subclasses must implement this method")


@dataclass
class Paper(Neo4jNode):
    """Paper node model for arXiv papers.
    
    Only core identification data is stored in Neo4j.
    Additional content (abstract, URLs) is stored in DynamoDB.
    """
    title: Optional[str] = None
    date: Optional[Union[date, str]] = None
    
    def __post_init__(self):
        """Initialize labels and properties after creation."""
        self.labels = ["Paper"]
        
        if not self.id:
            raise ValueError("Paper ID must be provided")
            
        validate_node_data("Paper", {
            "id": self.id,
            "title": self.title,
            "date": self.date
        }, ["id", "title"])
        
        self.properties = {
            "id": self.id,
            "title": self.title,
            "date": self.date
        }
    
    @classmethod
    def from_neo4j_result(cls, record: Dict[str, Any]):
        """Create Paper instance from Neo4j query result."""
        if "p" not in record:
            raise ValueError("Neo4j result does not contain paper node 'p'")
            
        node = record["p"]
        props = dict(node.items())
        
        return cls(
            id=props.get("id"),
            title=props.get("title"),
            date=props.get("date")
        )
    
    @classmethod
    def from_arxiv_record(cls, record: Dict[str, Any]):
        """Create Paper instance from arXiv processor record."""
        return cls(
            id=record["identifier"],
            title=record["title"],
            date=record["date"]
        )


@dataclass
class Author(Neo4jNode):
    """Author node model."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    
    def __post_init__(self):
        """Initialize labels and properties after creation."""
        self.labels = ["Author"]
        
        if not self.id:
            name_key = f"{self.last_name.lower()}_{self.first_name.lower()}".replace(" ", "_")
            import hashlib
            hash_input = f"{self.first_name}|{self.last_name}".encode('utf-8')
            self.id = hashlib.md5(hash_input).hexdigest()
        
        if not self.full_name and (self.first_name or self.last_name):
            parts = []
            if self.first_name:
                parts.append(self.first_name)
            if self.last_name:
                parts.append(self.last_name)
            self.full_name = " ".join(parts)
        
        self.properties = {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name
        }
    
    @classmethod
    def from_neo4j_result(cls, record: Dict[str, Any]):
        """Create Author instance from Neo4j query result."""
        if "a" not in record:
            raise ValueError("Neo4j result does not contain author node 'a'")
            
        node = record["a"]
        props = dict(node.items())
        
        return cls(
            id=props.get("id"),
            first_name=props.get("first_name"),
            last_name=props.get("last_name"),
            full_name=props.get("full_name")
        )
    
    @classmethod
    def from_arxiv_author(cls, author_data: Dict[str, str]):
        """Create Author instance from arXiv author data."""
        return cls(
            first_name=author_data.get("first_name", ""),
            last_name=author_data.get("last_name", "")
        )
        
    @classmethod
    def create_merge_query(cls, first_name: str, last_name: str):
        """Create a Cypher query to find or create an author based on name.
        
        Args:
            first_name: Author's first name
            last_name: Author's last name
            
        Returns:
            Tuple of (query_string, parameters)
        """
        import hashlib
        hash_input = f"{first_name}|{last_name}".encode('utf-8')
        author_id = hashlib.md5(hash_input).hexdigest()
        
        full_name = f"{first_name} {last_name}".strip()
        
        query = """
        MERGE (a:Author {first_name: $first_name, last_name: $last_name})
        ON CREATE SET a.id = $id, a.full_name = $full_name
        RETURN a
        """
        
        params = {
            "first_name": first_name,
            "last_name": last_name,
            "id": author_id,
            "full_name": full_name
        }
        
        return query, params


@dataclass
class Category(Neo4jNode):
    """Category node model for arXiv categories."""
    code: Optional[str] = None
    name: Optional[str] = None
    
    def __post_init__(self):
        """Initialize labels and properties after creation."""
        self.labels = ["Category"]
        
        if not self.id and self.code:
            self.id = self.code
        
        validate_node_data("Category", {
            "id": self.id,
            "code": self.code
        }, ["id", "code"])
        
        self.properties = {
            "id": self.id,
            "code": self.code,
            "name": self.name
        }
    
    @classmethod
    def from_neo4j_result(cls, record: Dict[str, Any]):
        """Create Category instance from Neo4j query result."""
        if "c" not in record:
            raise ValueError("Neo4j result does not contain category node 'c'")
            
        node = record["c"]
        props = dict(node.items())
        
        return cls(
            id=props.get("id"),
            code=props.get("code"),
            name=props.get("name")
        )


@dataclass
class Set(Neo4jNode):
    """Set node model for arXiv sets (e.g., cs, math)."""
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    
    def __post_init__(self):
        """Initialize labels and properties after creation."""
        self.labels = ["Set"]
        
        if not self.id and self.code:
            self.id = self.code
        
        validate_node_data("Set", {
            "id": self.id,
            "code": self.code,
            "name": self.name
        }, ["id", "code"])
        
        self.properties = {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "description": self.description
        }
    
    @classmethod
    def from_neo4j_result(cls, record: Dict[str, Any]):
        """Create Set instance from Neo4j query result."""
        if "s" not in record:
            raise ValueError("Neo4j result does not contain set node 's'")
            
        node = record["s"]
        props = dict(node.items())
        
        return cls(
            id=props.get("id"),
            code=props.get("code"),
            name=props.get("name"),
            description=props.get("description")
        )


@dataclass
class Relationship:
    """Base class for Neo4j relationships."""
    type: str
    start_node: Neo4jNode
    end_node: Neo4jNode
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_cypher_create(self) -> str:
        """Convert relationship to Cypher CREATE statement."""
        start_labels = ":".join(self.start_node.labels)
        end_labels = ":".join(self.end_node.labels)
        
        props_str = format_cypher_properties(self.properties) if self.properties else ""
        props_part = f" {props_str}" if props_str else ""
        
        return f"""
        MATCH (a:{start_labels} {{id: '{self.start_node.id}'}})
        MATCH (b:{end_labels} {{id: '{self.end_node.id}'}})
        CREATE (a)-[r:{self.type}{props_part}]->(b)
        """
    
    def to_cypher_merge(self) -> str:
        """Convert relationship to Cypher MERGE statement."""
        start_labels = ":".join(self.start_node.labels)
        end_labels = ":".join(self.end_node.labels)
        
        props_str = format_cypher_properties(self.properties) if self.properties else ""
        props_part = f" {props_str}" if props_str else ""
        
        return f"""
        MATCH (a:{start_labels} {{id: '{self.start_node.id}'}})
        MATCH (b:{end_labels} {{id: '{self.end_node.id}'}})
        MERGE (a)-[r:{self.type}]->(b)
        {"SET r = " + props_str if self.properties else ""}
        """


@dataclass
class AuthoredBy(Relationship):
    """Relationship between Paper and Author."""
    position: Optional[int] = None
    
    def __post_init__(self):
        """Initialize relationship properties."""
        self.type = "AUTHORED_BY"
        self.properties = {}
        
        if self.position is not None:
            self.properties["position"] = self.position


@dataclass
class CategorizedAs(Relationship):
    """Relationship between Paper and Category."""
    is_primary: bool = False
    
    def __post_init__(self):
        """Initialize relationship properties."""
        self.type = "CATEGORIZED_AS"
        self.properties = {"is_primary": self.is_primary}


@dataclass
class BelongsTo(Relationship):
    """Relationship between Paper and Set."""
    
    def __post_init__(self):
        """Initialize relationship properties."""
        self.type = "BELONGS_TO"
        self.properties = {}
