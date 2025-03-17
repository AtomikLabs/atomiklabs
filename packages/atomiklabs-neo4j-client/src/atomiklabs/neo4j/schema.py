"""Neo4j schema management including constraints and indexes."""

from typing import Dict
import logging

logger = logging.getLogger(__name__)

CONSTRAINTS = [
    "CREATE CONSTRAINT paper_id_unique IF NOT EXISTS FOR (p:Paper) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT author_id_unique IF NOT EXISTS FOR (a:Author) REQUIRE a.id IS UNIQUE",
    "CREATE CONSTRAINT category_id_unique IF NOT EXISTS FOR (c:Category) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT set_id_unique IF NOT EXISTS FOR (s:Set) REQUIRE s.id IS UNIQUE",
    
    "CREATE CONSTRAINT paper_title_exists IF NOT EXISTS FOR (p:Paper) REQUIRE p.title IS NOT NULL",
    "CREATE CONSTRAINT author_name_exists IF NOT EXISTS FOR (a:Author) REQUIRE a.full_name IS NOT NULL",
    "CREATE CONSTRAINT category_code_exists IF NOT EXISTS FOR (c:Category) REQUIRE c.code IS NOT NULL",
    "CREATE CONSTRAINT set_code_exists IF NOT EXISTS FOR (s:Set) REQUIRE s.code IS NOT NULL"
]

INDEXES = [
    "CREATE INDEX paper_title_idx IF NOT EXISTS FOR (p:Paper) ON (p.title)",
    "CREATE INDEX author_fullname_idx IF NOT EXISTS FOR (a:Author) ON (a.full_name)",
    "CREATE INDEX author_lastname_idx IF NOT EXISTS FOR (a:Author) ON (a.last_name)",
    "CREATE INDEX category_name_idx IF NOT EXISTS FOR (c:Category) ON (c.name)",
    "CREATE INDEX paper_date_idx IF NOT EXISTS FOR (p:Paper) ON (p.date)"
]


def setup_schema(session):
    """Set up all constraints and indexes in the database.
    
    Args:
        session: Active Neo4j session
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        for constraint in CONSTRAINTS:
            logger.info(f"Creating constraint: {constraint}")
            session.run(constraint)
        
        for index in INDEXES:
            logger.info(f"Creating index: {index}")
            session.run(index)
            
        logger.info("Schema setup completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error setting up schema: {e}")
        return False


def verify_schema(session) -> Dict[str, Dict[str, bool]]:
    """Verify that all constraints and indexes exist in the database.
    
    Args:
        session: Active Neo4j session
    
    Returns:
        Dict with status of each constraint and index
    """
    result = {
        "constraints": {},
        "indexes": {}
    }
    
    try:
        constraints_query = "SHOW CONSTRAINTS"
        constraints_result = session.run(constraints_query)
        existing_constraints = [record["name"] for record in constraints_result]
        
        for constraint in CONSTRAINTS:
            constraint_name = constraint.split("CREATE CONSTRAINT ")[1].split(" IF NOT EXISTS")[0]
            result["constraints"][constraint_name] = constraint_name in existing_constraints
        
        indexes_query = "SHOW INDEXES"
        indexes_result = session.run(indexes_query)
        existing_indexes = [record["name"] for record in indexes_result]
        
        for index in INDEXES:
            index_name = index.split("CREATE INDEX ")[1].split(" IF NOT EXISTS")[0]
            result["indexes"][index_name] = index_name in existing_indexes
            
        return result
    except Exception as e:
        logger.error(f"Error verifying schema: {e}")
        return result


def drop_all_constraints(session):
    """Drop all constraints from the database.
    
    Args:
        session: Active Neo4j session
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        session.run("DROP CONSTRAINT paper_id_unique IF EXISTS")
        session.run("DROP CONSTRAINT author_id_unique IF EXISTS")
        session.run("DROP CONSTRAINT category_id_unique IF EXISTS") 
        session.run("DROP CONSTRAINT set_id_unique IF EXISTS")
        session.run("DROP CONSTRAINT paper_title_exists IF EXISTS")
        session.run("DROP CONSTRAINT author_name_exists IF EXISTS")
        session.run("DROP CONSTRAINT category_code_exists IF EXISTS")
        session.run("DROP CONSTRAINT set_code_exists IF EXISTS")
        logger.info("All constraints dropped")
        return True
    except Exception as e:
        logger.error(f"Error dropping constraints: {e}")
        return False


def drop_all_indexes(session):
    """Drop all indexes from the database.
    
    Args:
        session: Active Neo4j session
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        session.run("DROP INDEX paper_title_idx IF EXISTS")
        session.run("DROP INDEX author_fullname_idx IF EXISTS")
        session.run("DROP INDEX author_lastname_idx IF EXISTS")
        session.run("DROP INDEX category_name_idx IF EXISTS")
        session.run("DROP INDEX paper_date_idx IF EXISTS")
        logger.info("All indexes dropped")
        return True
    except Exception as e:
        logger.error(f"Error dropping indexes: {e}")
        return False 