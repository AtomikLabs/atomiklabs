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
    subnet_ids         = data.aws_subnets.default.ids
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      CONFIG_PATH = "/${var.project}/${var.environment}"
      DEPLOY_TIMESTAMP = timestamp()
      # Add database connection info
      DB_HOST = aws_db_instance.postgresql.address
      DB_PORT = aws_db_instance.postgresql.port
      DB_NAME = aws_db_instance.postgresql.db_name
      DB_USER = aws_db_instance.postgresql.username
      DB_PASSWORD_PARAM = aws_ssm_parameter.db_password.name
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
