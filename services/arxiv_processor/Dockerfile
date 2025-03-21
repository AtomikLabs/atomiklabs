FROM python:3.11-slim

WORKDIR /app

# Install build essentials for potential binary dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Use a pre-configured pip.conf with repository URL and token
COPY pip.conf /etc/pip.conf

# Install packages with dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    # Verify all packages are installed
    pip list | grep neo4j && \
    pip list | grep atomiklabs-neo4j-client

COPY src/ .

CMD ["python", "processor.py"] 