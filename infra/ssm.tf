# SSM parameters for Lambda functions
resource "aws_ssm_parameter" "s3_bucket" {
  name  = "/${var.project}/${var.environment}/arxiv/s3_bucket"
  type  = "String"
  value = aws_s3_bucket.storage.id
  tags  = local.common_tags
}

resource "aws_ssm_parameter" "arxiv_back_date" {
  name  = "/${var.project}/${var.environment}/arxiv/back_date"
  type  = "String"
  value = "3"  # Default to 3 days lookback
  tags  = local.common_tags
}

# Email configuration is still needed for the mailer function
resource "aws_ssm_parameter" "email_recipients" {
  name  = "/${var.project}/${var.environment}/arxiv/email/recipients"
  type  = "String"
  value = join(",", var.email_config.recipients)
  tags  = local.common_tags
} 