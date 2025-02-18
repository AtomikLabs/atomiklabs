locals {
  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  resource_prefix = "${var.project}-${var.environment}"
  resource_suffix = var.resource_uuid

  newsletter_bucket_name = "${local.resource_prefix}-newsletters-${local.resource_suffix}"
  metadata_table_name   = "${local.resource_prefix}-metadata-${local.resource_suffix}"
}
