resource "aws_ssm_parameter" "email_recipients" {
  name  = "/${var.project}/${var.environment}/arxiv/email/recipients"
  type  = "String"
  value = join(",", var.email_config.recipients)
  tags  = local.common_tags
} 