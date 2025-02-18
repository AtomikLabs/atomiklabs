output "arxiv_processor_repository_url" {
  value = aws_ecr_repository.arxiv_processor.repository_url
  description = "The URL of the ECR repository"
} 