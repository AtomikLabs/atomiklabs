resource "aws_lambda_layer_version" "shared" {
  filename         = "${path.module}/build/shared_layer.zip"
  layer_name      = "${local.resource_prefix}-shared-${local.resource_suffix}"
  description     = "Shared database interface layer"
  compatible_runtimes = ["python3.11"]
}

resource "aws_lambda_function" "mailer" {
  layers          = [aws_lambda_layer_version.shared.arn]
  filename         = "${path.module}/build/mailer.zip"
  function_name    = "${local.resource_prefix}-mailer-${local.resource_suffix}"
  role            = aws_iam_role.lambda_mailer.arn
  handler         = "mailer.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/build/mailer.zip")
  runtime         = "python3.11"
  timeout         = 60
  memory_size     = 256

  environment {
    variables = {
      CONFIG_PATH = "/${var.project}/${var.environment}"
      DEPLOY_TIMESTAMP = timestamp()
      DB_NAME = aws_db_instance.arxiv_db.db_name
      DB_USER = aws_db_instance.arxiv_db.username
      DB_HOST = aws_db_instance.arxiv_db.address
      DB_PORT = tostring(aws_db_instance.arxiv_db.port)
      DB_PASSWORD = aws_ssm_parameter.db_password.name  # We reference the SSM param name, not the value
    }
  }

  vpc_config {
    subnet_ids         = data.aws_subnets.default.ids
    security_group_ids = [aws_security_group.lambda_vpc.id]
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
          aws_ssm_parameter.arxiv_back_date.arn,
          aws_ssm_parameter.db_password.arn,
          aws_ssm_parameter.db_host.arn,
          aws_ssm_parameter.db_name.arn,
          aws_ssm_parameter.db_user.arn
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
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_mailer_basic" {
  role       = aws_iam_role.lambda_mailer.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_mailer_vpc" {
  role       = aws_iam_role.lambda_mailer.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_cloudwatch_log_group" "lambda_mailer" {
  name              = "/aws/lambda/${aws_lambda_function.mailer.function_name}"
  retention_in_days = 7
}
