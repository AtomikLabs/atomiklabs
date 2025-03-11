locals {
  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  resource_prefix = "${var.project}-${var.environment}"
  resource_suffix = var.resource_uuid

  storage_bucket_name = "${local.resource_prefix}-storage-${local.resource_suffix}"
  
  # Define API Gateway ID for use in policies
  api_gateway_id = aws_apigatewayv2_api.http_api.id
}
