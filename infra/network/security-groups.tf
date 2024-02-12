resource "aws_security_group" "app_sg" {
  name        = "app-sg-${var.environment}"
  description = "Security group for application in ${var.environment} environment"
  vpc_id      = aws_vpc.app_vpc.id

  # Example rule: allow inbound SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Example rule: allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "app-sg-${var.environment}"
  }
}
