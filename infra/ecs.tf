resource "aws_ecs_cluster" "arxiv" {
  name = "${local.resource_prefix}-cluster-${local.resource_suffix}"
}

resource "aws_ecs_cluster_capacity_providers" "arxiv" {
  cluster_name = aws_ecs_cluster.arxiv.name
  capacity_providers = ["FARGATE"]
  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = "FARGATE"
  }
}

resource "aws_iam_role" "ecs_task_role" {
  name = "${local.resource_prefix}-task-${substr(local.resource_suffix, 0, 8)}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_security_group" "ecs_tasks" {
  name        = "${local.resource_prefix}-ecs-tasks-${local.resource_suffix}"
  description = "Allow outbound traffic for ECS tasks"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_iam_role_policy" "ecs_task_policy" {
  name = "${local.resource_prefix}-task-policy-${substr(local.resource_suffix, 0, 8)}"
  role = aws_iam_role.ecs_task_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.storage.arn,
          "${aws_s3_bucket.storage.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:BatchWriteItem"
        ]
        Resource = [
          aws_dynamodb_table.newsletter_metadata.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project}/${var.environment}/arxiv/*",
        ]
      }
    ]
  })
}

resource "aws_iam_role" "ecs_execution_role" {
  name = "${local.resource_prefix}-exec-${substr(local.resource_suffix, 0, 8)}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_ecr_repository" "daily_processor" {
  name = "${local.resource_prefix}-daily-processor-${local.resource_suffix}"
  force_delete = true
}

resource "aws_ecs_task_definition" "arxiv_processor" {
  family                   = "${local.resource_prefix}-arxiv-processor-${local.resource_suffix}"
  requires_compatibilities = ["FARGATE"]
  network_mode            = "awsvpc"
  cpu                     = 1024
  memory                  = 2048
  task_role_arn           = aws_iam_role.ecs_task_role.arn
  execution_role_arn      = aws_iam_role.ecs_execution_role.arn

  container_definitions = jsonencode([
    {
      name  = "arxiv-processor"
      image = "${aws_ecr_repository.daily_processor.repository_url}:arxiv"
      environment = [
        { name = "CONFIG_PATH", value = "/${var.project}/${var.environment}" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/${local.resource_prefix}-arxiv-processor-${local.resource_suffix}"
          awslogs-region        = var.region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_task_definition" "nvd_checker" {
  family                   = "${local.resource_prefix}-nvd-checker-${local.resource_suffix}"
  requires_compatibilities = ["FARGATE"]
  network_mode            = "awsvpc"
  cpu                     = 512
  memory                  = 1024
  task_role_arn           = aws_iam_role.ecs_task_role.arn
  execution_role_arn      = aws_iam_role.ecs_execution_role.arn

  container_definitions = jsonencode([
    {
      name  = "nvd-checker"
      image = "${aws_ecr_repository.daily_processor.repository_url}:nvd"
      environment = [
        { name = "CONFIG_PATH", value = "/${var.project}/${var.environment}" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/${local.resource_prefix}-nvd-checker-${local.resource_suffix}"
          awslogs-region        = var.region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
} 