FROM python:3.11-slim

WORKDIR /app

# Copy and install shared library first
COPY shared/arxiv_common /tmp/arxiv_common
RUN pip install /tmp/arxiv_common

# Then install service-specific requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ .

CMD ["python", "processor.py"] 