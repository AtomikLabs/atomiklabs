# Shared Package

Common utilities shared between services.

## Database Interface

```python
from shared.db import SQLiteDB

# Create database instance
db = SQLiteDB('/path/to/db.sqlite')

# Execute query
result = db.execute('SELECT * FROM table WHERE id = ?', (1,))

# Use transaction
with db.transaction() as conn:
    db.execute('INSERT INTO table (name) VALUES (?)', ('test',))
    # Transaction automatically commits on success, rolls back on error
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
