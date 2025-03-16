output "ecr_repository_url" {
  description = "URL of the daily processor ECR repository"
  value       = aws_ecr_repository.atomiklabs_ecr.repository_url
}

output "lambda_function_name" {
  description = "Name of the mailer Lambda function"
  value       = aws_lambda_function.mailer.function_name
}

output "neo4j_instance_id" {
  description = "ID of the Neo4j EC2 instance"
  value       = aws_instance.neo4j[0].id
}

output "neo4j_instance_public_ip" {
  description = "Public IP address of the Neo4j EC2 instance"
  value       = aws_instance.neo4j[0].public_ip
}

output "neo4j_instance_public_dns" {
  description = "Public DNS name of the Neo4j EC2 instance"
  value       = aws_instance.neo4j[0].public_dns
}

output "neo4j_ebs_volume_id" {
  description = "ID of the Neo4j EBS volume"
  value       = aws_ebs_volume.neo4j_data.id
}

output "neo4j_ssh_command" {
  description = "SSH command to connect to the Neo4j instance"
  value       = "ssh ec2-user@${aws_instance.neo4j[0].public_dns}"
}

output "neo4j_eip" {
  description = "Elastic IP of the Neo4j instance"
  value       = aws_eip.neo4j.public_ip
}
