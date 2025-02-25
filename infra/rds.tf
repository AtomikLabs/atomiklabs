resource "aws_db_subnet_group" "atomiklabs" {
  name       = "${local.resource_prefix}-db-subnet-${local.resource_suffix}"
  subnet_ids = data.aws_subnets.default.ids
  tags       = local.common_tags
}

resource "aws_security_group" "rds" {
  name        = "${local.resource_prefix}-rds-sg-${local.resource_suffix}"
  description = "Allow database access from tasks and lambdas"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id, aws_security_group.lambda_vpc.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

resource "aws_db_instance" "arxiv_db" {
  identifier              = lower("${local.resource_prefix}-db-${local.resource_suffix}")
  engine                  = "postgres"
  engine_version          = "15.5"
  instance_class          = "db.t3.micro"  # Free tier eligible
  allocated_storage       = 20
  max_allocated_storage   = 100
  storage_type            = "gp2"
  db_name                 = "arxiv"
  username                = "arxiv_app"
  password                = random_password.db_password.result
  db_subnet_group_name    = aws_db_subnet_group.atomiklabs.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  backup_retention_period = 7
  skip_final_snapshot     = true
  apply_immediately       = true
  storage_encrypted       = true
  deletion_protection     = var.environment == "prod" ? true : false
  tags                    = local.common_tags
}

resource "random_password" "db_password" {
  length  = 16
  special = false
}

resource "aws_ssm_parameter" "db_password" {
  name  = "/${var.project}/${var.environment}/db/password"
  type  = "SecureString"
  value = random_password.db_password.result
  tags  = local.common_tags
}

resource "aws_ssm_parameter" "db_host" {
  name  = "/${var.project}/${var.environment}/db/host"
  type  = "String"
  value = aws_db_instance.arxiv_db.address
  tags  = local.common_tags
}

resource "aws_ssm_parameter" "db_name" {
  name  = "/${var.project}/${var.environment}/db/name"
  type  = "String"
  value = aws_db_instance.arxiv_db.db_name
  tags  = local.common_tags
}

resource "aws_ssm_parameter" "db_user" {
  name  = "/${var.project}/${var.environment}/db/user"
  type  = "String"
  value = aws_db_instance.arxiv_db.username
  tags  = local.common_tags
}
