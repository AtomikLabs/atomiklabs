resource "aws_security_group" "rds" {
  name        = "${local.resource_prefix}-rds-${local.resource_suffix}"
  description = "Allow PostgreSQL traffic for RDS"
  vpc_id      = data.aws_vpc.default.id

  # Allow PostgreSQL traffic from ECS tasks
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  # Allow PostgreSQL traffic from Lambda functions
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name      = "rds-security-group"
    Component = "database"
  })
}

# Generate a random password for the RDS instance
resource "random_password" "db_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Store the database credentials in AWS Secrets Manager
resource "aws_secretsmanager_secret" "db_credentials" {
  name        = "${local.resource_prefix}-db-credentials-${local.resource_suffix}"
  description = "Database credentials for RDS PostgreSQL"

  tags = merge(local.common_tags, {
    Name      = "db-credentials"
    Component = "database"
  })
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = local.db_username
    password = random_password.db_password.result
    engine   = "postgres"
    host     = aws_db_instance.postgres.address
    port     = 5432
    dbname   = local.db_name
  })
}

resource "aws_db_subnet_group" "postgres" {
  name       = "${local.resource_prefix}-db-subnet-group-${local.resource_suffix}"
  subnet_ids = data.aws_subnets.default.ids

  tags = merge(local.common_tags, {
    Name      = "db-subnet-group"
    Component = "database"
  })
}

# RDS PostgreSQL instance - free tier
resource "aws_db_instance" "postgres" {
  identifier             = "${local.resource_prefix}-postgres-${local.resource_suffix}"
  engine                 = "postgres"
  engine_version         = "17.3"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  storage_type           = "gp2"
  db_name                = local.db_name
  username               = local.db_username
  password               = random_password.db_password.result
  port                   = 5432
  parameter_group_name   = "default.postgres17"
  publicly_accessible    = false
  skip_final_snapshot    = true
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.postgres.name

  # Free tier settings
  backup_retention_period = 7
  multi_az                = false
  storage_encrypted       = true

  tags = merge(local.common_tags, {
    Name      = "postgres-db"
    Component = "database"
  })
} 