# API Gateway policy to restrict access to VPC endpoint

# For HTTP API Gateway, we need to use a different approach to restrict access
# We'll add a policy to the VPC endpoint instead

# Update the VPC endpoint policy to restrict access to the API Gateway
resource "aws_vpc_endpoint_policy" "api_gateway_endpoint_policy" {
  vpc_endpoint_id = aws_vpc_endpoint.api_gateway.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = "*"
        Action = "execute-api:Invoke"
        Resource = "${aws_apigatewayv2_api.http_api.execution_arn}/*"
      }
    ]
  })
}
