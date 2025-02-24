output "ecr_repository_url" {
  description = "URL of the services ECR repository"
  value       = aws_ecr_repository.services.repository_url
}

output "lambda_function_name" {
  description = "Name of the mailer Lambda function"
  value       = aws_lambda_function.mailer.function_name
}

output "db_init_task_definition" {
  description = "Name of the DB init task definition"
  value       = aws_ecs_task_definition.db_init.family
}
