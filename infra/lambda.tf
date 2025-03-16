resource "aws_lambda_function" "mailer" {
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
    }
  }

  tags = local.common_tags
}

resource "aws_iam_role" "lambda_mailer" {
  name = "${local.resource_prefix}-mail-${substr(local.resource_suffix, 0, 8)}"
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
  name = "${local.resource_prefix}-mail-policy-${substr(local.resource_suffix, 0, 8)}"
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
          "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project}/${var.environment}/arxiv/*"
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

resource "aws_cloudwatch_log_group" "lambda_mailer" {
  name              = "/aws/lambda/${aws_lambda_function.mailer.function_name}"
  retention_in_days = 7
}
