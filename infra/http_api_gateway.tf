# HTTP API Gateway - A simpler alternative to REST API Gateway

# Create a new HTTP API (much simpler than REST API)
resource "aws_apigatewayv2_api" "http_api" {
  name          = "${local.resource_prefix}-http-api"
  protocol_type = "HTTP"
  
  # Disable the default endpoint - we'll only use the VPC endpoint
  disable_execute_api_endpoint = true
}

# Create a stage
resource "aws_apigatewayv2_stage" "dev" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = var.environment
  auto_deploy = true
  
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.http_api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      errorMessage   = "$context.error.message"
      errorType      = "$context.error.responseType"
      authorizationType = "$context.authorizer.type"
    })
  }
}

# CloudWatch log group for HTTP API Gateway
resource "aws_cloudwatch_log_group" "http_api_gateway" {
  name              = "/aws/apigateway/${local.resource_prefix}-http-api"
  retention_in_days = 30

  tags = merge(
    local.common_tags,
    {
      Name = "${local.resource_prefix}-http-api-logs"
    }
  )
}

# Create routes for the HTTP API

# Papers routes
resource "aws_apigatewayv2_route" "get_papers" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /papers"
  
  # Enable IAM authorization
  authorization_type = "AWS_IAM"
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "get_paper" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /papers/{id}"
  
  # Enable IAM authorization
  authorization_type = "AWS_IAM"
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# Authors routes
resource "aws_apigatewayv2_route" "get_authors" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /authors"
  
  # Enable IAM authorization
  authorization_type = "AWS_IAM"
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "get_author" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /authors/{id}"
  
  # Enable IAM authorization
  authorization_type = "AWS_IAM"
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "get_paper_authors" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /papers/{id}/authors"
  
  # Enable IAM authorization
  authorization_type = "AWS_IAM"
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# Categories routes
resource "aws_apigatewayv2_route" "get_categories" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /categories"
  
  # Enable IAM authorization
  authorization_type = "AWS_IAM"
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "get_category" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /categories/{code}"
  
  # Enable IAM authorization
  authorization_type = "AWS_IAM"
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# Sets routes
resource "aws_apigatewayv2_route" "get_sets" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /sets"
  
  # Enable IAM authorization
  authorization_type = "AWS_IAM"
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "get_set" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /sets/{id}"
  
  # Enable IAM authorization
  authorization_type = "AWS_IAM"
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "get_set_by_code" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /sets/code/{code}"
  
  # Enable IAM authorization
  authorization_type = "AWS_IAM"
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# Abstract routes
resource "aws_apigatewayv2_route" "get_abstract" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /papers/{id}/abstract"
  
  # Enable IAM authorization
  authorization_type = "AWS_IAM"
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "put_abstract" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "PUT /papers/{id}/abstract"
  
  # Enable IAM authorization
  authorization_type = "AWS_IAM"
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "delete_abstract" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "DELETE /papers/{id}/abstract"
  
  # Enable IAM authorization
  authorization_type = "AWS_IAM"
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# Create the Lambda integration
resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id           = aws_apigatewayv2_api.http_api.id
  integration_type = "AWS_PROXY"
  
  integration_uri    = aws_lambda_function.arxiv_api.invoke_arn
  integration_method = "POST"
  payload_format_version = "2.0"
}

# Lambda permission for the HTTP API
resource "aws_lambda_permission" "http_api_gateway_lambda" {
  statement_id  = "AllowExecutionFromHTTPAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.arxiv_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

# Create a VPC Link for the HTTP API
resource "aws_apigatewayv2_vpc_link" "api_vpc_link" {
  name               = "${local.resource_prefix}-vpc-link"
  security_group_ids = [aws_security_group.vpc_endpoints.id]
  subnet_ids         = data.aws_subnets.private.ids
}

# Update the VPC endpoint policy to allow access to the HTTP API
resource "aws_vpc_endpoint_policy" "api_gateway_endpoint_policy" {
  vpc_endpoint_id = aws_vpc_endpoint.api_gateway.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = "execute-api:Invoke"
        Resource  = "*"
      }
    ]
  })
}

# Output the HTTP API Gateway URL
output "http_api_gateway_url" {
  value = "${aws_apigatewayv2_api.http_api.api_endpoint}/${var.environment}"
  description = "HTTP API Gateway URL"
}

# Output the HTTP API Gateway ID
output "http_api_gateway_id" {
  value = aws_apigatewayv2_api.http_api.id
  description = "HTTP API Gateway ID"
}
