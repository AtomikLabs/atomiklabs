resource "aws_ssm_parameter" "arxiv_sets" {
  name  = "${var.environment}/arxiv/sets"
  type  = "String"
  value = jsonencode(keys(var.arxiv_config.sets))
}

resource "aws_ssm_parameter" "arxiv_categories" {
  for_each = var.arxiv_config.sets
  
  name  = "${var.environment}/arxiv/${each.key}/categories"
  type  = "String"
  value = join(",", each.value.categories)
}

resource "aws_ssm_parameter" "arxiv_back_date" {
  for_each = var.arxiv_config.sets
  
  name  = "${var.environment}/arxiv/${each.key}/back_date"
  type  = "Number"
  value = each.value.back_date
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
  value = aws_s3_bucket.storage.id
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

resource "aws_ssm_parameter" "nvd_api_key" {
  name  = "/${var.project}/${var.environment}/nvd/nvd_api_key"
  type  = "SecureString"
  value = var.nvd_api_key
  tags  = local.common_tags
}

resource "aws_ssm_parameter" "nvd_monitored_systems" {
  name  = "/${var.project}/${var.environment}/nvd/monitored_systems"
  type  = "String"
  value = jsonencode(var.monitored_systems)
  tags  = local.common_tags
}

resource "aws_ssm_parameter" "nvd_s3_bucket" {
  name  = "/${var.project}/${var.environment}/nvd/s3_bucket"
  type  = "String"
  value = aws_s3_bucket.storage.id
  tags  = local.common_tags
}

resource "aws_ssm_parameter" "neo4j_password" {
  name  = "/${var.project}/${var.environment}/neo4j/password"
  type  = "SecureString"
  value = var.neo4j_password
  tags  = local.common_tags
}
