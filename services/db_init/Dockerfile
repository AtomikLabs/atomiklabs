ARG ECR_REPO
FROM ${ECR_REPO}:base

WORKDIR /app/db_init
COPY src/ src/
ENTRYPOINT ["python", "-m", "src.db_init"]
