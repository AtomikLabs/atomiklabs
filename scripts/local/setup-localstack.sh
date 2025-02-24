#!/bin/bash
set -e

# Initialize Terraform for local workspace
echo "Initializing Terraform..."
cd infra
terraform init
terraform workspace new local || terraform workspace select local
terraform apply -auto-approve
cd ..

# Create required directories
echo "Creating required directories..."
mkdir -p docker/efs/sqlite
mkdir -p docker/efs/sqlite-test

# Make init.sh executable
chmod +x docker/localstack/init.sh

# Start LocalStack and services
echo "Starting LocalStack and services..."
docker-compose -f docker/docker-compose.yml up -d localstack

# Check LocalStack health
echo "Checking LocalStack health..."
./scripts/local/check-localstack.sh

# Initialize LocalStack resources
echo "Initializing LocalStack resources..."
docker-compose -f docker/docker-compose.yml exec localstack /docker-entrypoint-initaws.d/init.sh

# Start db-init service to initialize the database
echo "Initializing SQLite database..."
docker-compose -f docker/docker-compose.yml --profile db up -d
sleep 5  # Give db-init time to complete

echo "Setup complete! Available commands:"
echo "- Start all services:     make start"
echo "- Run specific service:   make run-service PROFILE=<profile>"
echo "- View logs:             make logs"
echo "- Check health:          make check-health"
echo "- Open service shell:    make shell SERVICE=<service>"
echo ""
echo "Available profiles: processor, db, nvd, all"
echo ""
echo "For more commands, run: make help"
