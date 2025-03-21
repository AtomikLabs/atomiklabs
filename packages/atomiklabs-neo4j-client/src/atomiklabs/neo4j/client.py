"""Neo4j client for interacting with Neo4j graph database in atomiklabs."""

from typing import Optional, List, Dict, Any, TypeVar, cast
from types import TracebackType
import logging
from functools import wraps
from contextlib import contextmanager

from neo4j import GraphDatabase, Driver, Session, Transaction, Result

from .exceptions import (
    Neo4jError, 
    Neo4jConnectionError, 
    Neo4jAuthError, 
    Neo4jQueryError,
    Neo4jTransactionError,
    Neo4jNodeNotFoundError
)
from .models import (
    Neo4jNode, 
    Paper, 
    Author, 
    Category, 
    Set,
    Relationship,
    AuthoredBy,
    CategorizedAs,
    BelongsTo
)
from .schema import setup_schema, verify_schema

T = TypeVar('T')

logger = logging.getLogger(__name__)


def handle_neo4j_errors(func):
    """Decorator to handle Neo4j errors and convert them to custom exceptions."""
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Neo4jError:
            raise
        except Exception as e:
            error_msg = str(e)
            if "Failed to establish connection" in error_msg:
                raise Neo4jConnectionError(f"Failed to connect to Neo4j: {e}")
            elif "authentication failure" in error_msg.lower():
                raise Neo4jAuthError(f"Authentication failed: {e}")
            else:
                query = kwargs.get("query", "Unknown query")
                params = kwargs.get("parameters", {})
                raise Neo4jQueryError(f"Neo4j query error: {e}", query=query, params=params)
    
    return wrapper


class Neo4jClient:
    """Client for interacting with Neo4j database.
    
    Provides methods for:
    - Managing connections to Neo4j
    - Creating and retrieving nodes
    - Creating relationships between nodes
    - Running custom Cypher queries
    - Setting up schema (constraints and indexes)
    """
    
    def __init__(self, uri: str, username: str, password: str, database: str = "neo4j"):
        """Initialize Neo4j client.
        
        Args:
            uri: Neo4j server URI (e.g., "neo4j://hostname:7687")
            username: Neo4j username (typically "neo4j")
            password: Neo4j password
            database: Neo4j database name
        """
        self.uri = uri
        self.username = username
        self.database = database
        self._driver: Optional[Driver] = None
        
        try:
            self._driver = GraphDatabase.driver(uri, auth=(username, password))
            with self._driver.session(database=self.database) as session:
                session.run("RETURN 1").single()
            logger.info(f"Connected to Neo4j at {uri}")
        except Exception as e:
            if self._driver:
                self._driver.close()
                self._driver = None
            raise Neo4jConnectionError(f"Failed to connect to Neo4j: {e}")
    
    def __enter__(self):
        """Enter context manager."""
        return self
    
    def __exit__(
        self, 
        exc_type: Optional[type[BaseException]], 
        exc_val: Optional[BaseException], 
        exc_tb: Optional[TracebackType]
    ) -> None:
        """Exit context manager and close connection."""
        self.close()
    
    def close(self) -> None:
        """Close Neo4j driver connection."""
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")
    
    @contextmanager
    def session(self) -> Session:
        """Get a Neo4j session as a context manager.
        
        Yields:
            Neo4j session
        
        Raises:
            Neo4jConnectionError: If connection to Neo4j fails
        """
        if not self._driver:
            raise Neo4jConnectionError("Not connected to Neo4j")
        
        session = self._driver.session(database=self.database)
        try:
            yield session
        finally:
            session.close()
    
    @handle_neo4j_errors
    def setup_schema(self) -> bool:
        """Set up Neo4j schema with constraints and indexes.
        
        Returns:
            True if successful, False otherwise
        """
        with self.session() as session:
            return setup_schema(session)
    
    @handle_neo4j_errors
    def verify_schema(self) -> Dict[str, Dict[str, bool]]:
        """Verify that Neo4j schema is properly set up.
        
        Returns:
            Dict with status of each constraint and index
        """
        with self.session() as session:
            return verify_schema(session)
    
    @handle_neo4j_errors
    def run_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Result:
        """Run a custom Cypher query.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            Neo4j Result object
        """
        with self.session() as session:
            return session.run(query, parameters or {})
    
    @handle_neo4j_errors
    def create_node(self, node: Neo4jNode) -> Neo4jNode:
        """Create a node in Neo4j.
        
        Args:
            node: Neo4jNode instance
            
        Returns:
            The created node with ID updated
        """
        query = node.to_cypher_create() + " RETURN n"
        
        with self.session() as session:
            result = session.run(query)
            record = result.single()
            if not record:
                raise Neo4jQueryError("Failed to create node", query=query)
            
            return type(node).from_neo4j_result({"n": record["n"]})
    
    @handle_neo4j_errors
    def get_node_by_id(self, node_type: type[T], node_id: str) -> T:
        """Get a node by its ID.
        
        Args:
            node_type: Node class (Paper, Author, etc.)
            node_id: Node ID
            
        Returns:
            Node instance
            
        Raises:
            Neo4jNodeNotFoundError: If node not found
        """
        temp_node = node_type()
        labels = ":".join(temp_node.labels)
        
        query = f"MATCH (n:{labels} {{id: $id}}) RETURN n"
        
        with self.session() as session:
            result = session.run(query, {"id": node_id})
            record = result.single()
            if not record:
                raise Neo4jNodeNotFoundError(f"Node with ID {node_id} not found")
            
            node_var = next(iter(record.keys()))
            return cast(T, node_type.from_neo4j_result({node_var: record[node_var]}))
    
    @handle_neo4j_errors
    def create_relationship(self, relationship: Relationship) -> None:
        """Create a relationship between nodes.
        
        Args:
            relationship: Relationship instance
        """
        query = relationship.to_cypher_create()
        
        with self.session() as session:
            session.run(query)
    
    @handle_neo4j_errors
    def create_or_update_paper(self, paper: Paper) -> Paper:
        """Create or update a paper node.
        
        Args:
            paper: Paper instance
            
        Returns:
            Updated Paper instance
        """
        query = paper.to_cypher_merge() + " RETURN n"
        
        with self.session() as session:
            result = session.run(query)
            record = result.single()
            if not record:
                raise Neo4jQueryError("Failed to create/update paper", query=query)
            
            return Paper.from_neo4j_result({"n": record["n"]})
    
    @handle_neo4j_errors
    def create_or_get_author(self, first_name: str, last_name: str) -> Author:
        """Create or get an author by name.
        
        Args:
            first_name: Author's first name
            last_name: Author's last name
            
        Returns:
            Author instance
        """
        query, params = Author.create_merge_query(first_name, last_name)
        
        with self.session() as session:
            result = session.run(query, params)
            record = result.single()
            if not record:
                raise Neo4jQueryError("Failed to create/get author", query=query, params=params)
            
            return Author.from_neo4j_result({"a": record["a"]})
    
    @handle_neo4j_errors
    def create_or_get_category(self, code: str, name: Optional[str] = None) -> Category:
        """Create or get a category by code.
        
        Args:
            code: Category code
            name: Category name
            
        Returns:
            Category instance
        """
        query = """
        MERGE (c:Category {code: $code})
        ON CREATE SET c.id = $code
        """
        
        if name:
            query += ", c.name = $name"
        
        query += " RETURN c"
        
        with self.session() as session:
            result = session.run(query, {"code": code, "name": name})
            record = result.single()
            if not record:
                raise Neo4jQueryError("Failed to create/get category", query=query)
            
            return Category.from_neo4j_result({"c": record["c"]})
    
    @handle_neo4j_errors
    def create_or_get_set(self, code: str, name: Optional[str] = None, description: Optional[str] = None) -> Set:
        """Create or get a set by code.
        
        Args:
            code: Set code
            name: Set name
            description: Set description
            
        Returns:
            Set instance
        """
        query = """
        MERGE (s:Set {code: $code})
        ON CREATE SET s.id = $code
        """
        
        params = {"code": code}
        
        if name:
            query += ", s.name = $name"
            params["name"] = name
        
        if description:
            query += ", s.description = $description"
            params["description"] = description
        
        query += " RETURN s"
        
        with self.session() as session:
            result = session.run(query, params)
            record = result.single()
            if not record:
                raise Neo4jQueryError("Failed to create/get set", query=query)
            
            return Set.from_neo4j_result({"s": record["s"]})
    
    @handle_neo4j_errors
    def link_paper_to_author(self, paper: Paper, author: Author, position: Optional[int] = None) -> None:
        """Create AUTHORED_BY relationship between paper and author.
        
        Args:
            paper: Paper instance
            author: Author instance
            position: Author position (optional)
        """
        authored_by = AuthoredBy(
            start_node=paper,
            end_node=author,
            position=position
        )
        self.create_relationship(authored_by)
    
    @handle_neo4j_errors
    def link_paper_to_category(self, paper: Paper, category: Category, is_primary: bool = False) -> None:
        """Create CATEGORIZED_AS relationship between paper and category.
        
        Args:
            paper: Paper instance
            category: Category instance
            is_primary: Whether this is the primary category
        """
        categorized_as = CategorizedAs(
            start_node=paper,
            end_node=category,
            is_primary=is_primary
        )
        self.create_relationship(categorized_as)
    
    @handle_neo4j_errors
    def link_paper_to_set(self, paper: Paper, set_node: Set) -> None:
        """Create BELONGS_TO relationship between paper and set.
        
        Args:
            paper: Paper instance
            set_node: Set instance
        """
        belongs_to = BelongsTo(
            start_node=paper,
            end_node=set_node
        )
        self.create_relationship(belongs_to)
    
    @handle_neo4j_errors
    def create_arxiv_paper_graph(self, paper_data: Dict[str, Any]) -> Paper:
        """Create complete graph structure for an arXiv paper.
        
        Creates:
        - Paper node
        - Author nodes
        - Category nodes
        - Set node
        - All relationships
        
        Args:
            paper_data: arXiv paper data dictionary
            
        Returns:
            Created Paper instance
        """
        # Start a transaction
        with self.session() as session:
            with session.begin_transaction() as tx:
                try:
                    paper = Paper.from_arxiv_record(paper_data)
                    query = paper.to_cypher_merge() + " RETURN n"
                    result = tx.run(query)
                    record = result.single()
                    paper = Paper.from_neo4j_result({"n": record["n"]})
                    
                    set_code = paper_data.get("set", "cs")
                    set_query = "MERGE (s:Set {code: $code}) ON CREATE SET s.id = $code RETURN s"
                    set_result = tx.run(set_query, {"code": set_code})
                    set_record = set_result.single()
                    set_node = Set.from_neo4j_result({"s": set_record["s"]})
                    
                    tx.run(f"""
                    MATCH (p:Paper {{id: $paper_id}}), (s:Set {{code: $set_code}})
                    MERGE (p)-[:BELONGS_TO]->(s)
                    """, {"paper_id": paper.id, "set_code": set_code})
                    
                    for i, author_data in enumerate(paper_data.get("authors", [])):
                        author_query, author_params = Author.create_merge_query(
                            author_data.get("first_name", ""),
                            author_data.get("last_name", "")
                        )
                        tx.run(author_query, author_params)
                        
                        author_id = author_params["id"]
                        tx.run(f"""
                        MATCH (p:Paper {{id: $paper_id}}), (a:Author {{id: $author_id}})
                        MERGE (p)-[r:AUTHORED_BY]->(a)
                        SET r.position = $position
                        """, {"paper_id": paper.id, "author_id": author_id, "position": i})
                    
                    categories = paper_data.get("categories", [])
                    primary_category = paper_data.get("primary_category")
                    
                    for category_code in categories:
                        tx.run(f"""
                        MERGE (c:Category {{code: $code}})
                        ON CREATE SET c.id = $code
                        """, {"code": category_code})
                        
                        is_primary = category_code == primary_category
                        tx.run(f"""
                        MATCH (p:Paper {{id: $paper_id}}), (c:Category {{code: $category_code}})
                        MERGE (p)-[r:CATEGORIZED_AS]->(c)
                        SET r.is_primary = $is_primary
                        """, {
                            "paper_id": paper.id, 
                            "category_code": category_code,
                            "is_primary": is_primary
                        })
                    
                    return paper
                except Exception as e:
                    tx.rollback()
                    raise Neo4jTransactionError(f"Transaction failed: {e}")
    
    @handle_neo4j_errors
    def get_papers_by_category(self, category_code: str, limit: int = 100) -> List[Paper]:
        """Get papers by category.
        
        Args:
            category_code: Category code
            limit: Maximum number of papers to return
            
        Returns:
            List of Paper instances
        """
        query = """
        MATCH (p:Paper)-[:CATEGORIZED_AS]->(c:Category {code: $category_code})
        RETURN p
        LIMIT $limit
        """
        
        with self.session() as session:
            result = session.run(query, {"category_code": category_code, "limit": limit})
            return [Paper.from_neo4j_result({"p": record["p"]}) for record in result]
    
    @handle_neo4j_errors
    def get_papers_by_author(self, author_id: str, limit: int = 100) -> List[Paper]:
        """Get papers by author ID.
        
        Args:
            author_id: Author ID
            limit: Maximum number of papers to return
            
        Returns:
            List of Paper instances
        """
        query = """
        MATCH (p:Paper)-[:AUTHORED_BY]->(a:Author {id: $author_id})
        RETURN p
        LIMIT $limit
        """
        
        with self.session() as session:
            result = session.run(query, {"author_id": author_id, "limit": limit})
            return [Paper.from_neo4j_result({"p": record["p"]}) for record in result]
    
    @handle_neo4j_errors
    def get_coauthors(self, author_id: str, limit: int = 100) -> List[Author]:
        """Get coauthors of an author.
        
        Args:
            author_id: Author ID
            limit: Maximum number of coauthors to return
            
        Returns:
            List of Author instances
        """
        query = """
        MATCH (a1:Author {id: $author_id})<-[:AUTHORED_BY]-(p:Paper)-[:AUTHORED_BY]->(a2:Author)
        WHERE a1 <> a2
        RETURN a2, count(p) AS paper_count
        ORDER BY paper_count DESC
        LIMIT $limit
        """
        
        with self.session() as session:
            result = session.run(query, {"author_id": author_id, "limit": limit})
            return [Author.from_neo4j_result({"a": record["a2"]}) for record in result]
    
    @handle_neo4j_errors
    def get_related_papers(self, paper_id: str, limit: int = 10) -> List[Paper]:
        """Get papers related to a given paper by shared categories.
        
        Args:
            paper_id: Paper ID
            limit: Maximum number of related papers to return
            
        Returns:
            List of related Paper instances
        """
        query = """
        MATCH (p1:Paper {id: $paper_id})-[:CATEGORIZED_AS]->(c:Category)<-[:CATEGORIZED_AS]-(p2:Paper)
        WHERE p1 <> p2
        RETURN p2, count(c) AS category_count
        ORDER BY category_count DESC
        LIMIT $limit
        """
        
        with self.session() as session:
            result = session.run(query, {"paper_id": paper_id, "limit": limit})
            return [Paper.from_neo4j_result({"p": record["p2"]}) for record in result]
