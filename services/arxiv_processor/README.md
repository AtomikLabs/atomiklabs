# ArXiv Processor

An ECS task for fetching and processing ArXiv papers.

## Overview

This service fetches papers from ArXiv based on configuration for sets and categories, processes them into our data models, and stores them in the database via the API Gateway. It also stores the full abstracts in S3.

## Features

- Configurable ArXiv sets and categories
- Date range filtering
- Batch processing
- Handling of LaTeX content in abstracts
- Integration with API Gateway for data storage
- S3 storage for full abstracts
- Error handling and retries

## Development

### Prerequisites

- Python 3.11+
- Poetry 1.x or 2.x (with export plugin for 2.x)
- Access to ArXiv API
- Access to API Gateway

### Setup

1. Install dependencies:

   ```bash
   cd services/arxiv_processor
   poetry install
   ```

2. Set up environment variables:

   ```bash
   export ARXIV_CATEGORIES=cs.AI,cs.CL
   export ARXIV_SETS=cs
   export DAYS_LOOKBACK=3
   export BATCH_SIZE=10
   export API_ENDPOINT=http://localhost:8080
   ```

   Alternatively, set up parameters in AWS SSM Parameter Store and use:

   ```bash
   export CONFIG_SSM_PATH=/arxiv/processor
   ```

### Running Tests

Run the tests with:

```bash
poetry run pytest
```

Run with coverage report:

```bash
poetry run pytest --cov=src --cov-report=term-missing
```

### Local Testing

For local testing, you can use the test script:

```bash
poetry run python src/test_run.py
```

## Deployment

The service is deployed as a Docker container to AWS ECS. The Dockerfile is located in the root of the service directory.

To build the Docker image:

```bash
docker build -t arxiv-processor:latest .
```

## Configuration

The service can be configured using environment variables or AWS SSM Parameter Store.

### Environment Variables

- `ARXIV_CATEGORIES`: Comma-separated list of ArXiv categories (e.g., "cs.AI,cs.CL")
- `ARXIV_SETS`: Comma-separated list of ArXiv sets (e.g., "cs,math")
- `DAYS_LOOKBACK`: Number of days to look back (default: 3)
- `BATCH_SIZE`: Number of papers to process in a batch (default: 10)
- `API_ENDPOINT`: API Gateway endpoint URL
- `S3_ABSTRACT_PREFIX`: Prefix for S3 abstract storage (default: "abstracts/")
- `CONFIG_SSM_PATH`: Path to AWS SSM Parameter Store for configuration

## Project Structure

- `src/`: Source code
  - `config.py`: Configuration management
  - `arxiv_fetcher.py`: ArXiv API client
  - `paper_processor.py`: Processing papers into our data models
  - `api_client.py`: API Gateway client
  - `main.py`: Main entry point
- `tests/`: Test code
  - `unit/`: Unit tests
  - `conftest.py`: Test fixtures
- `pyproject.toml`: Project configuration
- `poetry.toml`: Poetry configuration
- `export_requirements.py`: Script for exporting dependencies
- `Dockerfile`: Docker configuration
