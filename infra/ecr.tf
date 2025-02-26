resource "aws_ecr_repository" "daily_processor" {
  name = "${local.resource_prefix}-daily-processor-${local.resource_suffix}"
  force_delete = true
}

output "ecr_repository_url" {
  value = aws_ecr_repository.daily_processor.repository_url
} 