FROM python:3.11-slim

WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy pyproject.toml from shared package
COPY shared/pyproject.toml shared/

# Install only runtime dependencies from shared package
RUN cd shared && poetry export -f requirements.txt --output /tmp/requirements.txt --without-dev --without-hashes \
    && pip install -r /tmp/requirements.txt

# Copy shared package code
COPY shared /app/shared

# Copy service code
COPY services/arxiv_processor/src /app/

# Set environment variables
ENV PYTHONPATH=/app

# Run the service
CMD ["python", "main.py"] 