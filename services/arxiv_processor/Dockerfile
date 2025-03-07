FROM python:3.11-slim

WORKDIR /app

# Copy requirements files
COPY services/arxiv_processor/requirements.txt /app/requirements.txt
COPY shared/requirements.txt /app/shared_requirements.txt

# Install dependencies
RUN pip install -r /app/requirements.txt -r /app/shared_requirements.txt

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