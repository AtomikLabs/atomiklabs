# AtomikLabs Data Layer

This package provides the data access layer for the AtomikLabs research data system.

## Features

- SQLAlchemy ORM models for all data entities
- Repository pattern for database operations
- Database connection management with AWS Secrets Manager support
- Alembic migrations for schema evolution

## Installation

Install the package in development mode:

```bash
pip install -e .
```

## Database Setup

### Local Development

1. Set up environment variables for database connection:

```bash
export DB_USERNAME=postgres
export DB_PASSWORD=yourlocalpassword
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=atomiklabs
```

2. Initialize the database schema:

```bash
init-db
```

### Production

The database connection in production uses AWS Secrets Manager. Set the following environment variable:

```bash
export DB_CREDENTIALS_SECRET=atomiklabs-dev-db-credentials-xyz
```

## Database Migrations

This package uses Alembic for database migrations. Use the `db-migrate` command to manage migrations.

### Creating a Migration

To create a new migration manually:

```bash
db-migrate revision -m "Create users table"
```

To auto-generate a migration from model changes:

```bash
db-migrate revision -m "Add email to users" -a
```

### Running Migrations

To upgrade the database to the latest version:

```bash
db-migrate upgrade
```

To downgrade to a specific version:

```bash
db-migrate downgrade --revision abc123
```

### Checking Migration Status

To see the current database version:

```bash
db-migrate current
```

To show migration history:

```bash
db-migrate history
```

## Usage

```python
from data_layer import get_session, ArticleRepository, CategoryRepository

# Get a database session
with get_session() as session:
    # Create a category
    category = CategoryRepository.create_category(
        session=session,
        name="Machine Learning",
        code="cs.LG"
    )
    
    # Create an article
    article = ArticleRepository.create_article(
        session=session,
        source_id="2104.12345",
        source="arxiv",
        title="Advances in Machine Learning",
        publication_date="2023-01-15"
    )
    
    # Add the category to the article
    ArticleRepository.add_category_to_article(
        session=session,
        article_id=article.id,
        category_id=category.id,
        is_primary=True
    )
```
