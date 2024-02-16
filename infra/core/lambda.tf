resource "aws_iam_role" "lambda_execution_role" {
  name = "${local.environment}-lambda_exec_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_lambda_function" "fetch_daily_summaries" {
  function_name = "${local.environment}-fetch_daily_summaries"
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.repo.repository_url}:fetch_daily_summaries-latest"
  role          = aws_iam_role.lambda_execution_role.arn
  timeout       = 900
  memory_size   = 128

  environment {
    variables = {
      APP_NAME    = local.name
      ENVIRONMENT = local.environment
      GLUE_DATABASE_NAME = aws_glue_catalog_database.data_catalog_database.name
      GLUE_TABLE_NAME    = aws_glue_catalog_table.data_ingestion_metadata_table.name 
      S3_BUCKET   = aws_s3_bucket.atomiklabs_data_bucket.arn
      S3_STORAGE_KEY_PREFIX = local.data_ingestion_metadata_key_prefix
    }  
  }
}

resource "aws_iam_role_policy_attachment" "lambda_glue_policy_attach" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_glue_policy.arn
}
