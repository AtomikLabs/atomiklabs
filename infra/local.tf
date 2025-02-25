provider "aws" {
  alias                       = "local"
  region                      = "us-west-2"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  # LocalStack endpoint configuration
  endpoints {
    s3         = "http://localhost:4566"
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
  is_local_environment = terraform.workspace == "local" || var.environment == "local"
}

# Override resource configurations for local development
resource "aws_s3_bucket" "storage" {
  count         = local.is_local_environment ? 1 : 0
  provider      = aws.local
  bucket        = "${local.local_resource_prefix}-storage-${local.local_resource_suffix}"
  force_destroy = true
}

# Local SSM parameters
resource "aws_ssm_parameter" "arxiv_categories" {
  count    = local.is_local_environment ? 1 : 0
  provider = aws.local
  name     = "/arxiv/local/arxiv_categories"
  type     = "String"
  value    = "cs.AI,cs.LG,cs.CL"
}

resource "aws_ssm_parameter" "arxiv_back_date" {
  count    = local.is_local_environment ? 1 : 0
  provider = aws.local
  name     = "/arxiv/local/arxiv_back_date"
  type     = "String"
  value    = "2024-01-01"
}

resource "aws_ssm_parameter" "arxiv_set" {
  count    = local.is_local_environment ? 1 : 0
  provider = aws.local
  name     = "/arxiv/local/arxiv_set"
  type     = "String"
  value    = "cs"
}

resource "aws_ssm_parameter" "s3_bucket" {
  count    = local.is_local_environment ? 1 : 0
  provider = aws.local
  name     = "/arxiv/local/s3_bucket"
  type     = "String"
  value    = local.is_local_environment ? aws_s3_bucket.storage[0].id : ""
}

resource "aws_ssm_parameter" "nvd_api_key" {
  count    = local.is_local_environment ? 1 : 0
  provider = aws.local
  name     = "/arxiv/local/nvd_api_key"
  type     = "SecureString"
  value    = "dummy-api-key"
}

resource "aws_ssm_parameter" "nvd_monitored_systems" {
  count    = local.is_local_environment ? 1 : 0
  provider = aws.local
  name     = "/arxiv/local/nvd_monitored_systems"
  type     = "String"
  value    = "python,tensorflow,pytorch"
}

resource "aws_ssm_parameter" "nvd_s3_bucket" {
  count    = local.is_local_environment ? 1 : 0
  provider = aws.local
  name     = "/arxiv/local/nvd_s3_bucket"
  type     = "String"
  value    = local.is_local_environment ? aws_s3_bucket.storage[0].id : ""
}

resource "aws_ssm_parameter" "email_recipients" {
  count    = local.is_local_environment ? 1 : 0
  provider = aws.local
  name     = "/arxiv/local/email_recipients"
  type     = "String"
  value    = "test@example.com"
}

# Local SES configuration
resource "aws_ses_email_identity" "test" {
  count    = local.is_local_environment ? 1 : 0
  provider = aws.local
  email    = "test@example.com"
}
