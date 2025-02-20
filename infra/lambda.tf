data "archive_file" "mailer" {
  type        = "zip"
  source_dir  = "${path.module}/../services/arxiv_mailer/src"
  output_path = "${path.module}/build/mailer.zip"
}

resource "aws_lambda_function" "mailer" {
  filename         = data.archive_file.mailer.output_path
  function_name    = "${local.resource_prefix}-mailer-${local.resource_suffix}"
  role            = aws_iam_role.lambda_mailer.arn
  handler         = "mailer.lambda_handler"
  source_code_hash = filebase64sha256(data.archive_file.mailer.output_path)
  runtime         = "python3.11"
  timeout         = 60
  memory_size     = 256

  environment {
    variables = {
      CONFIG_PATH = "/${var.project}/${var.environment}/arxiv"
      DEPLOY_TIMESTAMP = timestamp()
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
          "dynamodb:Query",
          "dynamodb:GetItem"
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
          aws_ssm_parameter.arxiv_categories.arn,
          aws_ssm_parameter.s3_bucket.arn,
          aws_ssm_parameter.dynamodb_table.arn,
          aws_ssm_parameter.email_recipients.arn
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
