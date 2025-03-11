output "ecr_repository_url" {
  description = "URL of the daily processor ECR repository"
  value       = aws_ecr_repository.daily_processor.repository_url
}

output "lambda_function_name" {
  description = "Name of the mailer Lambda function"
  value       = aws_lambda_function.mailer.function_name
}

output "postgresql_endpoint" {
  description = "The connection endpoint for the PostgreSQL RDS instance"
  value       = aws_db_instance.postgresql.endpoint
}

output "postgresql_db_name" {
  description = "The database name"
  value       = aws_db_instance.postgresql.db_name
}

output "postgresql_username" {
  description = "The master username for the database"
  value       = aws_db_instance.postgresql.username
}

output "postgresql_password_param" {
  description = "The SSM parameter name for the database password"
  value       = aws_ssm_parameter.db_password.name
}

output "rest_api_gateway_url" {
  description = "The URL of the REST API Gateway (only accessible from within VPC via endpoint)"
  value       = "${aws_api_gateway_deployment.main.invoke_url}${aws_api_gateway_stage.main.stage_name}/"
}

output "rest_api_gateway_id" {
  description = "The ID of the API Gateway REST API"
  value       = aws_api_gateway_rest_api.main.id
}

output "http_api_gateway_url" {
  description = "The URL of the HTTP API Gateway (only accessible from within VPC via endpoint)"
  value       = "${aws_apigatewayv2_api.http_api.api_endpoint}/${aws_apigatewayv2_stage.dev.name}"
}

output "http_api_gateway_id" {
  description = "The ID of the API Gateway HTTP API"
  value       = aws_apigatewayv2_api.http_api.id
}

output "api_gateway_vpc_endpoint_id" {
  description = "The ID of the VPC endpoint for API Gateway"
  value       = aws_vpc_endpoint.api_gateway.id
}

output "api_lambda_function_name" {
  description = "Name of the arXiv API Lambda function"
  value       = aws_lambda_function.arxiv_api.function_name
}
