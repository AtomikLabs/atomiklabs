FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.7.1

# Set Poetry to not use virtual environments
RUN poetry config virtualenvs.create false

# Set up working directory
WORKDIR /app

# Copy Poetry configuration
COPY pyproject.toml poetry.lock* ./

# Copy the data layer package
COPY services/data_layer/ /app/services/data_layer/

# Copy the arxiv processor
COPY services/arxiv_processor/ /app/services/arxiv_processor/

# Install dependencies
RUN poetry install --no-interaction --no-ansi --no-dev

# Command to run the processor
CMD ["python", "-m", "services.arxiv_processor.src.processor"] 