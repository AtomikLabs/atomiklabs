provider "aws" {
  region                      = "us-west-2"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  # LocalStack endpoint configuration
  endpoints {
    s3         = "http://localhost:4566"
    efs        = "http://localhost:4566"
    ssm        = "http://localhost:4566"
    ses        = "http://localhost:4566"
    lambda     = "http://localhost:4566"
    cloudwatch = "http://localhost:4566"
    iam        = "http://localhost:4566"
  }
}

# Local workspace specific variables
locals {
  local_resource_prefix = "arxiv-local"
  local_resource_suffix = "dev"
}

# Override resource configurations for local development
resource "aws_s3_bucket" "storage" {
  bucket        = "${local.local_resource_prefix}-storage-${local.local_resource_suffix}"
  force_destroy = true
}

resource "aws_efs_file_system" "sqlite_storage" {
  creation_token = "${local.local_resource_prefix}-efs-${local.local_resource_suffix}"
  tags = {
    Name = "sqlite-storage"
  }
}

resource "aws_efs_access_point" "sqlite_data" {
  file_system_id = aws_efs_file_system.sqlite_storage.id
  root_directory {
    path = "/sqlite"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "755"
    }
  }
}

# Local SSM parameters
resource "aws_ssm_parameter" "arxiv_categories" {
  name  = "/arxiv/local/arxiv_categories"
  type  = "String"
  value = "cs.AI,cs.LG,cs.CL"
}

resource "aws_ssm_parameter" "arxiv_back_date" {
  name  = "/arxiv/local/arxiv_back_date"
  type  = "String"
  value = "2024-01-01"
}

resource "aws_ssm_parameter" "arxiv_set" {
  name  = "/arxiv/local/arxiv_set"
  type  = "String"
  value = "cs"
}

resource "aws_ssm_parameter" "s3_bucket" {
  name  = "/arxiv/local/s3_bucket"
  type  = "String"
  value = aws_s3_bucket.storage.id
}

resource "aws_ssm_parameter" "nvd_api_key" {
  name  = "/arxiv/local/nvd_api_key"
  type  = "SecureString"
  value = "dummy-api-key"
}

resource "aws_ssm_parameter" "nvd_monitored_systems" {
  name  = "/arxiv/local/nvd_monitored_systems"
  type  = "String"
  value = "python,tensorflow,pytorch"
}

resource "aws_ssm_parameter" "nvd_s3_bucket" {
  name  = "/arxiv/local/nvd_s3_bucket"
  type  = "String"
  value = aws_s3_bucket.storage.id
}

resource "aws_ssm_parameter" "email_recipients" {
  name  = "/arxiv/local/email_recipients"
  type  = "String"
  value = "test@example.com"
}

# Local SES configuration
resource "aws_ses_email_identity" "test" {
  email = "test@example.com"
}
