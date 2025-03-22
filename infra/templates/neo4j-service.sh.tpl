#!/bin/bash
set -e

# Install Docker
amazon-linux-extras install docker -y
systemctl enable docker
systemctl start docker

# Create data directories
mkdir -p /data/neo4j/data
mkdir -p /data/neo4j/logs
mkdir -p /data/neo4j/import
mkdir -p /data/neo4j/plugins
chmod -R 755 /data/neo4j

# Get password from SSM
NEO4J_PASSWORD=$(aws ssm get-parameter --name "/${project}/${environment}/neo4j/password" --with-decryption --query "Parameter.Value" --output text --region ${region})

# Run Neo4j container
docker run -d \
  --name neo4j \
  --restart=always \
  -p 7474:7474 \
  -p 7687:7687 \
  -v /data/neo4j/data:/data \
  -v /data/neo4j/logs:/logs \
  -v /data/neo4j/import:/import \
  -v /data/neo4j/plugins:/plugins \
  -e "NEO4J_AUTH=neo4j/$NEO4J_PASSWORD" \
  -e "NEO4J_dbms_connector_bolt_advertised__address=0.0.0.0:7687" \
  -e "NEO4J_dbms_connector_bolt_listen__address=0.0.0.0:7687" \
  -e "NEO4J_dbms_default__listen__address=0.0.0.0" \
  neo4j:latest

# Wait for Neo4j to start
echo "Waiting for Neo4j to start..."
sleep 20

echo "Neo4j setup complete!"