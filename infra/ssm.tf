resource "aws_ssm_parameter" "arxiv_categories" {
  name  = "/${var.project}/${var.environment}/arxiv/categories"
  type  = "String"
  value = join(",", var.arxiv_config.categories)
  tags  = local.common_tags
}

resource "aws_ssm_parameter" "arxiv_back_date" {
  name  = "/${var.project}/${var.environment}/arxiv/back_date"
  type  = "String"
  value = tostring(var.arxiv_config.back_date)
  tags  = local.common_tags
}

resource "aws_ssm_parameter" "arxiv_set" {
  name  = "/${var.project}/${var.environment}/arxiv/set"
  type  = "String"
  value = var.arxiv_config.arxiv_set
  tags  = local.common_tags
}

resource "aws_ssm_parameter" "s3_bucket" {
  name  = "/${var.project}/${var.environment}/arxiv/s3_bucket"
  type  = "String"
  value = aws_s3_bucket.newsletters.id
  tags  = local.common_tags
}

resource "aws_ssm_parameter" "dynamodb_table" {
  name  = "/${var.project}/${var.environment}/arxiv/dynamodb_table"
  type  = "String"
  value = aws_dynamodb_table.newsletter_metadata.id
  tags  = local.common_tags
}

resource "aws_ssm_parameter" "email_recipients" {
  name  = "/${var.project}/${var.environment}/arxiv/email/recipients"
  type  = "String"
  value = join(",", var.email_config.recipients)
  tags  = local.common_tags
} 