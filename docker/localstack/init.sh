#!/bin/bash

# Wait for LocalStack to be ready
echo "Waiting for LocalStack to be ready..."
while ! nc -z localhost 4566; do
  sleep 1
done

# Set default AWS CLI configuration
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-west-2
export ENDPOINT_URL="http://localhost:4566"

echo "Creating S3 bucket..."
awslocal s3 mb s3://arxiv-papers

echo "Creating SSM parameters..."
awslocal ssm put-parameter \
  --name "/arxiv/local/arxiv_categories" \
  --type "String" \
  --value "cs.AI,cs.LG,cs.CL"

awslocal ssm put-parameter \
  --name "/arxiv/local/arxiv_back_date" \
  --type "String" \
  --value "2024-01-01"

awslocal ssm put-parameter \
  --name "/arxiv/local/arxiv_set" \
  --type "String" \
  --value "cs"

awslocal ssm put-parameter \
  --name "/arxiv/local/s3_bucket" \
  --type "String" \
  --value "arxiv-papers"

awslocal ssm put-parameter \
  --name "/arxiv/local/nvd_api_key" \
  --type "SecureString" \
  --value "dummy-api-key"

awslocal ssm put-parameter \
  --name "/arxiv/local/nvd_monitored_systems" \
  --type "String" \
  --value "python,tensorflow,pytorch"

awslocal ssm put-parameter \
  --name "/arxiv/local/nvd_s3_bucket" \
  --type "String" \
  --value "arxiv-papers"

awslocal ssm put-parameter \
  --name "/arxiv/local/email_recipients" \
  --type "String" \
  --value "test@example.com"

# Create SES verified identity for testing
echo "Setting up SES..."
awslocal ses verify-email-identity --email-address test@example.com

# Create IAM roles and policies
echo "Creating IAM roles..."
awslocal iam create-role \
  --role-name ecs-task-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

awslocal iam create-role \
  --role-name lambda-mailer-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Create EFS file system (simulated in LocalStack)
echo "Setting up EFS..."
awslocal efs create-file-system \
  --creation-token arxiv-efs \
  --tags Key=Name,Value=sqlite-storage

echo "LocalStack initialization complete!"
