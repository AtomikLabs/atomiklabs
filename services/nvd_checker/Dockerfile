ARG ECR_REPO
FROM ${ECR_REPO}:base

WORKDIR /app/nvd_checker
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ .

CMD ["python", "nvd_checker.py"]
