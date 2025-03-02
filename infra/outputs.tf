output "ecr_repository_url" {
  description = "URL of the daily processor ECR repository"
  value       = aws_ecr_repository.daily_processor.repository_url
}

output "lambda_function_name" {
  description = "Name of the mailer Lambda function"
  value       = aws_lambda_function.mailer.function_name
}

output "db_host" {
  description = "The hostname of the PostgreSQL RDS instance"
  value       = replace(aws_db_instance.postgresql.endpoint, ":${aws_db_instance.postgresql.port}", "")
}

output "db_port" {
  description = "The port of the PostgreSQL RDS instance"
  value       = aws_db_instance.postgresql.port
}

output "db_name" {
  description = "The database name"
  value       = aws_db_instance.postgresql.db_name
}

output "db_username" {
  description = "The master username for the database"
  value       = aws_db_instance.postgresql.username
}

output "db_password_param" {
  description = "The SSM parameter name for the database password"
  value       = aws_ssm_parameter.db_password.name
}
