output "arxiv_processor_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.arxiv_processor.repository_url
}

output "lambda_function_name" {
  description = "Name of the mailer Lambda function"
  value       = aws_lambda_function.mailer.function_name
}
