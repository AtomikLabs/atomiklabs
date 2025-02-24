ARG ECR_REPO
FROM ${ECR_REPO}:base

WORKDIR /app/processor
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ .

CMD ["python", "processor.py"]
