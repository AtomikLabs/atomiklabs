FROM python:3.11-slim

WORKDIR /app

# Copy and install shared library first
COPY shared/arxiv_common /tmp/arxiv_common
RUN pip install /tmp/arxiv_common

# Then install service-specific requirements
COPY services/nvd_checker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/nvd_checker/src/ .

CMD ["python", "checker.py"] 