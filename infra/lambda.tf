locals {
  # Database connection details
  db_host     = "atomiklabs-dev-db-custom.cluster-xxxxxxxxx.region.rds.amazonaws.com"
  db_port     = 5432
  db_name     = "atomiklabs"
  db_username = "dbadmin"
}

resource "aws_lambda_function" "mailer" {
  filename         = "${path.module}/build/mailer.zip"
  function_name    = "${local.resource_prefix}-mailer-${local.resource_suffix}"
  role            = aws_iam_role.lambda_mailer.arn
  handler         = "mailer.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/build/mailer.zip")
  runtime         = "python3.11"
  timeout         = 180
  memory_size     = 256
  
  # Add the shared layer to the function
  layers          = [aws_lambda_layer_version.shared_layer.arn]

  vpc_config {
    subnet_ids         = data.aws_subnets.private.ids
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      CONFIG_PATH = "/${var.project}/${var.environment}"
      DEPLOY_TIMESTAMP = timestamp()
      # Use local variables for database connection info to avoid direct references
      DB_HOST = local.db_host
      DB_PORT = local.db_port
      DB_NAME = local.db_name
      DB_USER = local.db_username
      DB_PASSWORD_PARAM = aws_ssm_parameter.db_password.name
    }
  }

  tags = local.common_tags
  
  # Add a lifecycle rule to create the new Lambda before destroying the old one
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_iam_role" "lambda_mailer" {
  name = "${local.resource_prefix}-mail-${local.resource_suffix}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_mailer" {
  name = "${local.resource_prefix}-lambda-mailer-policy-${local.resource_suffix}"
  role = aws_iam_role.lambda_mailer.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          aws_ssm_parameter.s3_bucket.arn,
          aws_ssm_parameter.email_recipients.arn,
          aws_ssm_parameter.arxiv_back_date.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetObject"
        ]
        Resource = [
          aws_s3_bucket.storage.arn,
          "${aws_s3_bucket.storage.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "rds-db:connect",
          "rds:DescribeDBInstances",
          "rds:DescribeDBClusters",
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          aws_db_instance.postgresql.arn,
          aws_ssm_parameter.db_password.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:AssignPrivateIpAddresses",
          "ec2:UnassignPrivateIpAddresses"
        ]
        Resource = ["*"]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_mailer_basic" {
  role       = aws_iam_role.lambda_mailer.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "lambda_mailer" {
  name              = "/aws/lambda/${aws_lambda_function.mailer.function_name}"
  retention_in_days = 7
}

# arXiv Data Layer API Lambda function
resource "aws_lambda_function" "arxiv_api" {
  filename         = "${path.module}/build/arxiv_api.zip"
  function_name    = "${local.resource_prefix}-api-${local.resource_suffix}"
  role            = aws_iam_role.lambda_arxiv_api.arn
  handler         = "index.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/build/arxiv_api.zip")
  runtime         = "python3.11"
  timeout         = 60
  memory_size     = 512
  
  # Add the shared layer to the function
  layers          = [aws_lambda_layer_version.shared_layer.arn]

  vpc_config {
    subnet_ids         = data.aws_subnets.private.ids
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      CONFIG_PATH = "/${var.project}/${var.environment}"
      DEPLOY_TIMESTAMP = timestamp()
      # Use local variables for database connection info to avoid direct references
      DB_HOST = local.db_host
      DB_PORT = local.db_port
      DB_NAME = local.db_name
      DB_USER = local.db_username
      DB_PASSWORD_PARAM = aws_ssm_parameter.db_password.name
      # Add logging configuration
      LOG_LEVEL = "INFO"
      POWERTOOLS_SERVICE_NAME = "arxiv-api"
      POWERTOOLS_METRICS_NAMESPACE = "ArxivAPI"
    }
  }

  tags = local.common_tags
  
  # Add a lifecycle rule to create the new Lambda before destroying the old one
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_iam_role" "lambda_arxiv_api" {
  name = "${local.resource_prefix}-api-${local.resource_suffix}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_arxiv_api" {
  name = "${local.resource_prefix}-lambda-api-policy-${local.resource_suffix}"
  role = aws_iam_role.lambda_arxiv_api.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          aws_ssm_parameter.s3_bucket.arn,
          aws_ssm_parameter.arxiv_back_date.arn,
          aws_ssm_parameter.email_recipients.arn,
          aws_ssm_parameter.db_password.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:GetObjectAttributes"
        ]
        Resource = [
          aws_s3_bucket.storage.arn,
          "${aws_s3_bucket.storage.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "execute-api:Invoke"
        ]
        Resource = [
          "arn:aws:execute-api:${var.region}:${data.aws_caller_identity.current.account_id}:${local.http_api_gateway_id}/${var.environment}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "rds-db:connect",
          "rds:DescribeDBInstances",
          "rds:DescribeDBClusters",
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          aws_db_instance.postgresql.arn,
          aws_ssm_parameter.db_password.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:AssignPrivateIpAddresses",
          "ec2:UnassignPrivateIpAddresses"
        ]
        Resource = ["*"]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_arxiv_api_basic" {
  role       = aws_iam_role.lambda_arxiv_api.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "lambda_arxiv_api" {
  name              = "/aws/lambda/${aws_lambda_function.arxiv_api.function_name}"
  retention_in_days = 7
}
