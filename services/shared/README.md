# Shared Package

Common utilities shared between services.

## Database Interface

```python
from shared.db import PostgresDB

# Create database instance with default environment variables
db = PostgresDB()

# Or provide connection parameters explicitly
db = PostgresDB({
    'host': 'localhost',
    'port': '5432',
    'user': 'arxiv_app',
    'password': 'password',
    'dbname': 'arxiv'
})

# Execute query
result = db.execute('SELECT * FROM papers WHERE id = %s', (1,))

# Use transaction
with db.transaction() as conn:
    cursor = conn.cursor()
    cursor.execute('INSERT INTO papers (arxiv_id) VALUES (%s)', ('2401.12345',))
    # Transaction automatically commits on success, rolls back on error
    
# Query helpers
paper = db.query_one('SELECT * FROM papers WHERE id = %s', (1,))
papers = db.query_all('SELECT * FROM papers LIMIT 10')
```

## Installation

From service directory:

```bash
pip install -e ../shared
```

## Docker Base Image

Services can use the shared base image:

```dockerfile
ARG ECR_REPO
FROM ${ECR_REPO}:base

WORKDIR /app/service
...
