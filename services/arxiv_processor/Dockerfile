FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Create data layer package directory
RUN mkdir -p /app/packages/atomiklabs_data

# Copy data_layer package
COPY services/data_layer/src/atomiklabs_data/ /app/packages/atomiklabs_data/
COPY services/data_layer/setup.py /app/packages/

# Copy requirements files first for better caching
COPY pyproject.toml poetry.lock* ./

# Copy the arxiv processor
COPY services/arxiv_processor/ /app/services/arxiv_processor/

# Install the data_layer package properly
RUN pip install --no-cache-dir /app/packages/

# Verify data_layer package installation
RUN python -c "import atomiklabs_data; print('Successfully imported atomiklabs_data')"

# Install Poetry for dependency management
RUN pip install --no-cache-dir poetry==1.7.1

# Configure Poetry to not use virtual environments
RUN poetry config virtualenvs.create false

# Install project dependencies
RUN poetry install --no-interaction --no-ansi --no-dev

# Set Python path to ensure packages can be found
ENV PYTHONPATH=/app:$PYTHONPATH

# Add health check to verify imports
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import atomiklabs_data; print('Container healthy')" || exit 1

# Command to run the processor
CMD ["python", "-m", "services.arxiv_processor.src.processor"] 