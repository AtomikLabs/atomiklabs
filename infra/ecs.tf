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
  name = "${local.resource_prefix}-task-${local.resource_suffix}"
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

resource "aws_iam_role_policy" "ecs_task_policy" {
  name = "${local.resource_prefix}-ecs-task-policy-${local.resource_suffix}"
  role = aws_iam_role.ecs_task_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket",
          "rds-db:connect",
          "rds:DescribeDBInstances",
          "rds:DescribeDBClusters"
        ]
        Resource = [
          aws_s3_bucket.storage.arn,
          "${aws_s3_bucket.storage.arn}/*",
          aws_db_instance.postgresql.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "execute-api:Invoke"
        ]
        Resource = [
          "arn:aws:execute-api:${var.region}:${data.aws_caller_identity.current.account_id}:*/*/*/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeVpcEndpoints",
          "ec2:DescribeRouteTables",
          "ec2:CreateRoute",
          "ec2:DeleteRoute"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role" "ecs_execution_role" {
  name = "${local.resource_prefix}-exec-${local.resource_suffix}"
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

  # Updated container definitions with enhanced logging for better troubleshooting
  container_definitions = jsonencode([
    {
      name  = "arxiv-processor"
      image = "${aws_ecr_repository.daily_processor.repository_url}:arxiv"
      environment = [
        # For private APIs, use the VPC endpoint DNS name and include the API ID
        { name = "API_ENDPOINT", value = "https://${aws_vpc_endpoint.api_gateway.dns_entry[0]["dns_name"]}/${var.environment}" },
        { name = "X_APIGW_API_ID", value = aws_api_gateway_rest_api.main.id },
        { name = "AWS_REGION", value = var.region },
        { name = "LOG_LEVEL", value = "DEBUG" }
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

# Create ECS service to run the task
resource "aws_ecs_service" "arxiv_processor" {
  name            = "${local.resource_prefix}-arxiv-processor-${local.resource_suffix}"
  cluster         = aws_ecs_cluster.arxiv.id
  task_definition = aws_ecs_task_definition.arxiv_processor.arn
  desired_count   = 0  # Set to 0 initially, will be triggered by EventBridge
  launch_type     = "FARGATE"
  
  # Force a new deployment to use the latest task definition with enhanced logging
  force_new_deployment = true

  # Configure network settings to use the VPC
  network_configuration {
    subnets          = data.aws_subnets.private.ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false  # Ensure tasks use private IPs only to route through VPC endpoints
  }
} 