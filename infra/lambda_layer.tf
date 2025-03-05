resource "aws_lambda_layer_version" "shared_layer" {
  layer_name = "${local.resource_prefix}-shared-layer-${local.resource_suffix}"
  description = "Shared models and constants for arXiv data processing"
  
  filename = "${path.module}/build/shared_layer.zip"
  source_code_hash = filebase64sha256("${path.module}/build/shared_layer.zip")
  
  compatible_runtimes = ["python3.9", "python3.10", "python3.11"]
}

output "shared_layer_arn" {
  description = "ARN of the shared Lambda layer"
  value       = aws_lambda_layer_version.shared_layer.arn
} 