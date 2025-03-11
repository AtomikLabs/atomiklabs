# API Gateway policy to restrict access to VPC endpoint

# Create a policy document to restrict access to the API Gateway
resource "aws_api_gateway_rest_api_policy" "api_gateway_policy" {
  rest_api_id = aws_apigatewayv2_api.http_api.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = "*"
        Action = "execute-api:Invoke"
        Resource = "${aws_apigatewayv2_api.http_api.execution_arn}/*"
        Condition = {
          StringEquals = {
            "aws:SourceVpce" = aws_vpc_endpoint.api_gateway.id
          }
        }
      },
      {
        Effect = "Allow"
        Principal = {
          AWS = [
            aws_iam_role.lambda_arxiv_api.arn,
            aws_iam_role.ecs_task_role.arn
          ]
        }
        Action = "execute-api:Invoke"
        Resource = "${aws_apigatewayv2_api.http_api.execution_arn}/*"
      }
    ]
  })
}
