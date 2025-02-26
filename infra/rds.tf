# PostgreSQL RDS instance configuration
resource "aws_db_subnet_group" "postgresql" {
  name       = "${local.resource_prefix}-subnet-group-${local.resource_suffix}"
  subnet_ids = data.aws_subnets.default.ids

  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-subnet-group"
  })
}

resource "aws_security_group" "postgresql" {
  name        = "${local.resource_prefix}-postgresql-sg-${local.resource_suffix}"
  description = "Allow PostgreSQL inbound traffic from ECS tasks and Lambda"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "PostgreSQL from ECS tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  ingress {
    description     = "PostgreSQL from Lambda"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-postgresql-sg"
  })
}

resource "aws_db_parameter_group" "postgresql" {
  name   = "${local.resource_prefix}-pg-params-${local.resource_suffix}"
  family = "postgres17"

  tags = local.common_tags
}

resource "aws_db_instance" "postgresql" {
  identifier             = "${local.resource_prefix}-db-${local.resource_suffix}"
  allocated_storage      = 20
  db_name                = "atomiklabs"
  engine                 = "postgres"
  engine_version         = "17.3"
  instance_class         = "db.t4g.micro"
  username               = "dbadmin"
  password               = aws_ssm_parameter.db_password.value
  parameter_group_name   = aws_db_parameter_group.postgresql.name
  skip_final_snapshot    = true
  vpc_security_group_ids = [aws_security_group.postgresql.id]
  db_subnet_group_name   = aws_db_subnet_group.postgresql.name
  publicly_accessible    = false
  storage_encrypted      = true
  deletion_protection    = false

  # Free tier eligible settings
  backup_retention_period = 0
  multi_az                = false
  storage_type            = "gp2"

  tags = local.common_tags
}

# Store the database password in SSM Parameter Store
resource "aws_ssm_parameter" "db_password" {
  name        = "/${var.project}/${var.environment}/db_password"
  description = "PostgreSQL database password"
  type        = "SecureString"
  value       = random_password.db_password.result

  tags = local.common_tags
}

# Generate a random password for the database
resource "random_password" "db_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Create a security group for Lambda functions
resource "aws_security_group" "lambda_sg" {
  name        = "${local.resource_prefix}-lambda-sg-${local.resource_suffix}"
  description = "Security group for Lambda functions to access RDS"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-lambda-sg"
  })
} 