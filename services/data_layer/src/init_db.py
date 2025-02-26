#!/usr/bin/env python3
"""
Database initialization script.

This script creates all database tables and populates
initial reference data like categories.
"""

import argparse
import logging
import os
import sys

from .db import init_db, create_tables, get_session
from .repository import CategoryRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_arxiv_categories(connection_string=None):
    """
    Initialize arXiv categories in the database.
    
    Args:
        connection_string: Optional database connection string
    """
    if connection_string:
        init_db(connection_string)
    
    # List of arXiv CS categories
    cs_categories = [
        {"code": "cs.AI", "name": "Artificial Intelligence"},
        {"code": "cs.AR", "name": "Hardware Architecture"},
        {"code": "cs.CC", "name": "Computational Complexity"},
        {"code": "cs.CE", "name": "Computational Engineering, Finance, and Science"},
        {"code": "cs.CG", "name": "Computational Geometry"},
        {"code": "cs.CL", "name": "Computation and Language"},
        {"code": "cs.CR", "name": "Cryptography and Security"},
        {"code": "cs.CV", "name": "Computer Vision and Pattern Recognition"},
        {"code": "cs.CY", "name": "Computers and Society"},
        {"code": "cs.DB", "name": "Databases"},
        {"code": "cs.DC", "name": "Distributed, Parallel, and Cluster Computing"},
        {"code": "cs.DL", "name": "Digital Libraries"},
        {"code": "cs.DM", "name": "Discrete Mathematics"},
        {"code": "cs.DS", "name": "Data Structures and Algorithms"},
        {"code": "cs.ET", "name": "Emerging Technologies"},
        {"code": "cs.FL", "name": "Formal Languages and Automata Theory"},
        {"code": "cs.GL", "name": "General Literature"},
        {"code": "cs.GR", "name": "Graphics"},
        {"code": "cs.GT", "name": "Computer Science and Game Theory"},
        {"code": "cs.HC", "name": "Human-Computer Interaction"},
        {"code": "cs.IR", "name": "Information Retrieval"},
        {"code": "cs.IT", "name": "Information Theory"},
        {"code": "cs.LG", "name": "Machine Learning"},
        {"code": "cs.LO", "name": "Logic in Computer Science"},
        {"code": "cs.MA", "name": "Multiagent Systems"},
        {"code": "cs.MM", "name": "Multimedia"},
        {"code": "cs.MS", "name": "Mathematical Software"},
        {"code": "cs.NA", "name": "Numerical Analysis"},
        {"code": "cs.NE", "name": "Neural and Evolutionary Computing"},
        {"code": "cs.NI", "name": "Networking and Internet Architecture"},
        {"code": "cs.OH", "name": "Other Computer Science"},
        {"code": "cs.OS", "name": "Operating Systems"},
        {"code": "cs.PF", "name": "Performance"},
        {"code": "cs.PL", "name": "Programming Languages"},
        {"code": "cs.RO", "name": "Robotics"},
        {"code": "cs.SC", "name": "Symbolic Computation"},
        {"code": "cs.SD", "name": "Sound"},
        {"code": "cs.SE", "name": "Software Engineering"},
        {"code": "cs.SI", "name": "Social and Information Networks"},
        {"code": "cs.SY", "name": "Systems and Control"},
    ]
    
    # Create the parent CS category
    with get_session() as session:
        cs_parent = CategoryRepository.create_category(
            session=session,
            name="Computer Science",
            code="cs"
        )
        
        # Add all CS subcategories
        for category in cs_categories:
            CategoryRepository.create_category(
                session=session,
                name=category["name"],
                code=category["code"],
                parent_id=cs_parent.id
            )
            
        logger.info(f"Added {len(cs_categories)} CS categories")


def main():
    """Main function to initialize the database."""
    parser = argparse.ArgumentParser(description='Initialize the database')
    parser.add_argument('--connection-string', help='Database connection string')
    args = parser.parse_args()
    
    connection_string = args.connection_string
    
    # Initialize database connection
    if connection_string:
        init_db(connection_string)
    else:
        # Use environment variables
        init_db()
    
    try:
        # Create all tables
        logger.info("Creating database tables...")
        create_tables()
        logger.info("Database tables created successfully")
        
        # Set up initial data
        logger.info("Adding initial category data...")
        setup_arxiv_categories(connection_string)
        logger.info("Initial data setup complete")
        
        return 0
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 