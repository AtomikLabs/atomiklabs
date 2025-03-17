# Atomik Labs Neo4j Client

A simple client for interacting with Neo4j databases in Atomik Labs projects.

## Installation

```bash
pip install atomiklabs-neo4j-client
```

## Usage

```python
from atomiklabs.neo4j import hello_world
from atomiklabs.neo4j.client import Neo4jClient

# Say hello
print(hello_world())

# Create a client
client = Neo4jClient(
    uri="neo4j://localhost:7687", 
    user="neo4j", 
    password="password"
)

# Connect to database
client.connect()

# Run a query
result = client.query("MATCH (n) RETURN n LIMIT 10")
```

## License

Proprietary - Atomik Labs
