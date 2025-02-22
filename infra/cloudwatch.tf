resource "aws_cloudwatch_log_group" "arxiv_processor" {
  name              = "/ecs/${local.resource_prefix}-arxiv-processor-${local.resource_suffix}"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "nvd_checker" {
  name              = "/ecs/${local.resource_prefix}-nvd-checker-${local.resource_suffix}"
  retention_in_days = 7
} 