import os
import sqlite3
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DB_DIR = "/mnt/papers/db"
DB_PATH = os.path.join(DB_DIR, "app.db")

def init_db():
    """Initialize the SQLite database if it doesn't exist."""
    try:
        # Create db directory if it doesn't exist
        Path(DB_DIR).mkdir(parents=True, exist_ok=True)
        
        # Check if database already exists
        if os.path.exists(DB_PATH):
            logger.info(f"Database already exists at {DB_PATH}")
            # Verify we can connect to it
            conn = sqlite3.connect(DB_PATH)
            conn.close()
            logger.info("Successfully verified database connection")
            return
            
        logger.info(f"Creating new database at {DB_PATH}")
        
        # Create new database and schema
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Create schema
        cursor.executescript("""
            -- Papers table stores the core paper metadata
            CREATE TABLE papers (
                id TEXT PRIMARY KEY,  -- arXiv ID
                title TEXT NOT NULL,
                abstract TEXT NOT NULL,
                date DATE NOT NULL,  -- Publication date
                abstract_url TEXT NOT NULL,
                pdf_url TEXT NOT NULL,
                primary_category TEXT NOT NULL,
                processed_date TIMESTAMP NOT NULL,
                embedding_updated_at TIMESTAMP,
                embedding BLOB,  -- Store paper embeddings for similarity search
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Authors table for normalized author information
            CREATE TABLE authors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(first_name, last_name)
            );

            -- Paper-Author relationship table
            CREATE TABLE paper_authors (
                paper_id TEXT NOT NULL,
                author_id INTEGER NOT NULL,
                author_position INTEGER NOT NULL,  -- Order in the author list
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (paper_id, author_id),
                FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
                FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
            );

            -- Categories table for normalized category information
            CREATE TABLE categories (
                code TEXT PRIMARY KEY,  -- e.g., 'CS', 'AI', etc.
                name TEXT NOT NULL,  -- Full category name
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Paper-Category relationship table
            CREATE TABLE paper_categories (
                paper_id TEXT NOT NULL,
                category_code TEXT NOT NULL,
                is_primary BOOLEAN NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (paper_id, category_code),
                FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
                FOREIGN KEY (category_code) REFERENCES categories(code) ON DELETE CASCADE
            );

            -- Citations table for building citation graph
            CREATE TABLE citations (
                citing_paper_id TEXT NOT NULL,
                cited_paper_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (citing_paper_id, cited_paper_id),
                FOREIGN KEY (citing_paper_id) REFERENCES papers(id) ON DELETE CASCADE,
                FOREIGN KEY (cited_paper_id) REFERENCES papers(id) ON DELETE CASCADE
            );

            -- Paper analysis and metrics
            CREATE TABLE paper_metrics (
                paper_id TEXT PRIMARY KEY,
                citation_count INTEGER DEFAULT 0,
                reference_count INTEGER DEFAULT 0,
                attention_score FLOAT,  -- Computed based on various factors
                trending_score FLOAT,  -- For tracking emerging papers
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
            );

            -- Topic modeling results
            CREATE TABLE paper_topics (
                paper_id TEXT NOT NULL,
                topic_id INTEGER NOT NULL,
                confidence FLOAT NOT NULL,  -- Topic assignment confidence
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (paper_id, topic_id),
                FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
            );

            -- Create indexes for better query performance
            CREATE INDEX idx_papers_date ON papers(date);
            CREATE INDEX idx_papers_primary_category ON papers(primary_category);
            CREATE INDEX idx_paper_authors_author ON paper_authors(author_id);
            CREATE INDEX idx_paper_categories_category ON paper_categories(category_code);
            CREATE INDEX idx_citations_cited ON citations(cited_paper_id);
            CREATE INDEX idx_paper_metrics_scores ON paper_metrics(attention_score, trending_score);
            CREATE INDEX idx_paper_topics_topic ON paper_topics(topic_id);
        """)
        
        # Initialize categories table with known categories
        categories = [
            ('AI', 'Computer Science - Artificial Intelligence'),
            ('AR', 'Computer Science - Hardware Architecture'),
            ('CC', 'Computer Science - Computational Complexity'),
            ('CE', 'Computer Science - Computational Engineering, Finance, and Science'),
            ('CG', 'Computer Science - Computational Geometry'),
            ('CL', 'Computer Science - Computation and Language'),
            ('CR', 'Computer Science - Cryptography and Security'),
            ('CV', 'Computer Science - Computer Vision and Pattern Recognition'),
            ('CY', 'Computer Science - Computers and Society'),
            ('DB', 'Computer Science - Databases'),
            ('DC', 'Computer Science - Distributed, Parallel, and Cluster Computing'),
            ('DL', 'Computer Science - Digital Libraries'),
            ('DM', 'Computer Science - Discrete Mathematics'),
            ('DS', 'Computer Science - Data Structures and Algorithms'),
            ('ET', 'Computer Science - Emerging Technologies'),
            ('FL', 'Computer Science - Formal Languages and Automata Theory'),
            ('GL', 'Computer Science - General Literature'),
            ('GR', 'Computer Science - Graphics'),
            ('GT', 'Computer Science - Computer Science and Game Theory'),
            ('HC', 'Computer Science - Human-Computer Interaction'),
            ('IR', 'Computer Science - Information Retrieval'),
            ('IT', 'Computer Science - Information Theory'),
            ('LG', 'Computer Science - Machine Learning'),
            ('LO', 'Computer Science - Logic in Computer Science'),
            ('MA', 'Computer Science - Multiagent Systems'),
            ('MM', 'Computer Science - Multimedia'),
            ('MS', 'Computer Science - Mathematical Software'),
            ('NA', 'Computer Science - Numerical Analysis'),
            ('NE', 'Computer Science - Neural and Evolutionary Computing'),
            ('NI', 'Computer Science - Networking and Internet Architecture'),
            ('OH', 'Computer Science - Other Computer Science'),
            ('OS', 'Computer Science - Operating Systems'),
            ('PF', 'Computer Science - Performance'),
            ('PL', 'Computer Science - Programming Languages'),
            ('RO', 'Computer Science - Robotics'),
            ('SC', 'Computer Science - Symbolic Computation'),
            ('SD', 'Computer Science - Sound'),
            ('SE', 'Computer Science - Software Engineering'),
            ('SI', 'Computer Science - Social and Information Networks'),
            ('SY', 'Computer Science - Systems and Control')
        ]
        
        cursor.executemany(
            "INSERT INTO categories (code, name) VALUES (?, ?)",
            categories
        )
        
        conn.commit()
        conn.close()
        
        logger.info("Successfully initialized database with schema and category data")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

if __name__ == "__main__":
    init_db() 