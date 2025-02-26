# Create a Lambda layer for the data_layer package
resource "aws_lambda_layer_version" "data_layer" {
  filename   = "${path.module}/build/data_layer.zip"
  layer_name = "${local.resource_prefix}-data-layer-${local.resource_suffix}"

  compatible_runtimes = ["python3.11"]
  source_code_hash    = filebase64sha256("${path.module}/build/data_layer.zip")
}

resource "aws_lambda_function" "mailer" {
  function_name = "${local.resource_prefix}-mailer-${local.resource_suffix}"
  role          = aws_iam_role.lambda_mailer.arn
  timeout       = 60
  memory_size   = 256
  
  # Use container image instead of zip file
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.daily_processor.repository_url}:mailer"
  
  # Add ECR permissions to Lambda IAM role
  depends_on = [
    aws_ecr_repository.daily_processor,
    aws_iam_role_policy_attachment.lambda_mailer_ecr_pull
  ]
  
  # VPC configuration to allow RDS access
  vpc_config {
    subnet_ids         = data.aws_subnets.default.ids
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      CONFIG_PATH = "/${var.project}/${var.environment}"
      DEPLOY_TIMESTAMP = timestamp()
      DB_CREDENTIALS_SECRET = aws_secretsmanager_secret.db_credentials.name
    }
  }

  tags = local.common_tags
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
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${aws_s3_bucket.storage.arn}",
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
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project}/${var.environment}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.db_credentials.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_mailer_basic" {
  role       = aws_iam_role.lambda_mailer.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Allow Lambda to create network interfaces for VPC access
resource "aws_iam_role_policy_attachment" "lambda_mailer_vpc" {
  role       = aws_iam_role.lambda_mailer.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Add ECR pull permissions to the Lambda role
resource "aws_iam_role_policy" "lambda_mailer_ecr" {
  name = "${local.resource_prefix}-lambda-ecr-policy-${local.resource_suffix}"
  role = aws_iam_role.lambda_mailer.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
        Resource = [aws_ecr_repository.daily_processor.arn]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_mailer_ecr_pull" {
  role       = aws_iam_role.lambda_mailer.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonECR-ReadOnly"
}

resource "aws_cloudwatch_log_group" "lambda_mailer" {
  name              = "/aws/lambda/${aws_lambda_function.mailer.function_name}"
  retention_in_days = 14
}

