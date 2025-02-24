FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY scripts/ scripts/

# Create directory for SQLite database
RUN mkdir -p /mnt/papers/db && \
    chown -R 1000:1000 /mnt/papers

# Set the default user
USER 1000

CMD ["python", "src/main.py"] 