FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

# Use a pre-configured pip.conf with repository URL and token
COPY pip.conf /etc/pip.conf
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ .

CMD ["python", "processor.py"] 