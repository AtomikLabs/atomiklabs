
# Local Development with LocalStack

This directory contains the configuration for running the project locally using LocalStack to emulate AWS services.

## Prerequisites

- Docker and Docker Compose
- AWS CLI (for local development)
- Python 3.11+
- Terraform 1.0+

## Infrastructure Management

The local environment uses a dedicated Terraform workspace to manage AWS resources in LocalStack:

```bash
# The setup script automatically handles this, but you can also manually:
cd infra
terraform init
terraform workspace new local  # or 'terraform workspace select local'
terraform apply
```

This ensures local resources are managed consistently with the cloud environment, using:

- Local provider configuration in `infra/local.tf`
- Separate state for local resources
- Same resource structure as production

## Services Emulated

- S3: For storing papers and newsletters
- EFS: Simulated using Docker volumes for SQLite database
- SSM: For configuration parameters
- SES: For email sending (in test mode)
- Lambda: For the mailer function
- CloudWatch Logs: For service logging
- IAM: For roles and permissions

## Directory Structure

```
docker/
├── docker-compose.yml          # Main compose file
├── docker-compose.test.yml     # Test environment overrides
├── localstack/
│   └── init.sh                # LocalStack initialization script
└── efs/                       # Local EFS simulation
    ├── sqlite/                # Main SQLite database
    └── sqlite-test/           # Test environment database
```

## Getting Started

The project includes a Makefile to simplify common development tasks:

```bash
# View all available commands
make help

# Initial setup
make setup

# Start all services
make start

# Start specific services
docker-compose -f docker/docker-compose.yml up arxiv-processor nvd-checker

# View logs
make logs                              # All services
make logs-service SERVICE=db-init      # Specific service

# Run tests
make test                             # All services
make test-service SERVICE=db-init     # Specific service

# Terraform operations
make tf-local CMD=plan                # Plan local changes
make tf-local CMD=apply               # Apply local changes

# Cleanup
make clean                            # Remove all containers and volumes
```

The setup command will:

- Create necessary directories
- Initialize Terraform workspace
- Start LocalStack
- Initialize AWS resources
- Set up the SQLite database

## Testing

1. Run tests for a specific service:

   ```bash
   docker-compose -f docker/docker-compose.yml -f docker/docker-compose.test.yml up arxiv-processor
   ```

2. Run all tests:

   ```bash
   docker-compose -f docker/docker-compose.yml -f docker/docker-compose.test.yml up \
     arxiv-processor db-init nvd-checker
   ```

## Environment Variables

Each service is configured with:

- `AWS_ENDPOINT_URL=http://localstack:4566`
- `AWS_ACCESS_KEY_ID=test`
- `AWS_SECRET_ACCESS_KEY=test`
- `AWS_DEFAULT_REGION=us-west-2`
- `CONFIG_PATH=/arxiv/local` (or `/arxiv/test` for testing)

## Data Persistence

- SQLite database is stored in `docker/efs/sqlite/`
- Test database is stored in `docker/efs/sqlite-test/`
- LocalStack data is persisted in a Docker volume

## Troubleshooting

1. Reset LocalStack:

   ```bash
   docker-compose -f docker/docker-compose.yml down -v
   ./scripts/local/setup-localstack.sh
   ```

2. View logs:

   ```bash
   # LocalStack logs
   docker-compose -f docker/docker-compose.yml logs localstack

   # Service logs
   docker-compose -f docker/docker-compose.yml logs arxiv-processor
   ```

3. Common issues:
   - If services can't connect to LocalStack, ensure the `AWS_ENDPOINT_URL` is correct
   - If database initialization fails, check the db-init service logs
   - For permission issues, verify the LocalStack initialization completed successfully
