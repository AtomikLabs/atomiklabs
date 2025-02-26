output "ecr_repository_url" {
  description = "URL of the daily processor ECR repository"
  value       = aws_ecr_repository.daily_processor.repository_url
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.mailer.function_name
}

output "database_endpoint" {
  description = "Endpoint of the RDS PostgreSQL database"
  value       = aws_db_instance.postgres.endpoint
  sensitive   = true
}

output "database_credentials_secret" {
  description = "Name of the Secrets Manager secret containing database credentials"
  value       = aws_secretsmanager_secret.db_credentials.name
}

output "db_init_task_definition" {
  description = "Task definition ARN for the database initialization task"
  value       = aws_ecs_task_definition.db_init.arn
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.arxiv.name
}
