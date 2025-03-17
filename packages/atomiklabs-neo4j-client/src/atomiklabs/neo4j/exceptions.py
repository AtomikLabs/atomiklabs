class Neo4jError(Exception):
    """Base exception for all Neo4j client errors."""
    pass


class Neo4jConnectionError(Neo4jError):
    """Raised when connection to Neo4j database fails."""
    pass


class Neo4jAuthError(Neo4jError):
    """Raised when authentication with Neo4j fails."""
    pass


class Neo4jQueryError(Neo4jError):
    """Raised when a Cypher query fails to execute."""
    def __init__(self, message, query=None, params=None):
        self.query = query
        self.params = params
        super().__init__(f"{message} - Query: {query}, Params: {params}")


class Neo4jTransactionError(Neo4jError):
    """Raised when a Neo4j transaction fails."""
    pass


class Neo4jDataValidationError(Neo4jError):
    """Raised when data validation fails before insertion."""
    pass


class Neo4jNodeNotFoundError(Neo4jError):
    """Raised when a node cannot be found by ID or properties."""
    pass


class Neo4jConstraintViolationError(Neo4jError):
    """Raised when a Neo4j constraint is violated."""
    pass
