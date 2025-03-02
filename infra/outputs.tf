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
