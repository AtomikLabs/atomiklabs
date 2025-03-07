FROM python:3.11-slim

WORKDIR /app

# Install Poetry 2.x and the export plugin
RUN pip install "poetry>=2.0.0" poetry-plugin-export

# Copy pyproject.toml from shared package
COPY shared/pyproject.toml shared/

# Use poetry with the export plugin
RUN cd shared && \
    poetry config virtualenvs.create false && \
    poetry export --format requirements.txt --output /tmp/requirements.txt --without dev --without-hashes && \
    pip install -r /tmp/requirements.txt

# Copy shared package code
COPY shared /app/shared

# Copy service code
COPY services/arxiv_processor/src/*.py /app/

# Copy configuration
COPY services/arxiv_processor/config.json /app/config.json

# Set environment variables
ENV PYTHONPATH=/app

# Run the service
CMD ["python", "main.py"] 