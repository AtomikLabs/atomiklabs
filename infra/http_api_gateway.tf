# HTTP API Gateway - A simpler alternative to REST API Gateway

# Create a new HTTP API (much simpler than REST API)
resource "aws_apigatewayv2_api" "http_api" {
  name          = "${local.resource_prefix}-http-api"
  protocol_type = "HTTP"
  
  # Add explicit resource policy to allow access from VPC endpoint and ECS task role
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "PUT", "DELETE"]
    allow_headers = ["Content-Type", "Authorization", "X-Amz-Date", "X-Api-Key", "X-Amz-Security-Token"]
  }
  
  # Disable the default endpoint - we'll only use the VPC endpoint
  disable_execute_api_endpoint = false  # Enable for testing, can disable later
  
  # Route selection expression for HTTP API
  route_selection_expression = "$request.method $request.path"
}

# Create a stage
resource "aws_apigatewayv2_stage" "dev" {
  api_id      = aws_apigatewayv2_api.http_api.id  # Use direct reference to avoid circular dependency
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
  
  # No authorization - open access within VPC
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "get_paper" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /papers/{id}"
  
  # No authorization - open access within VPC
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# Authors routes
resource "aws_apigatewayv2_route" "get_authors" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /authors"
  
  # No authorization - open access within VPC
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "get_author" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /authors/{id}"
  
  # No authorization - open access within VPC
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "get_paper_authors" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /papers/{id}/authors"
  
  # No authorization - open access within VPC
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# Categories routes
resource "aws_apigatewayv2_route" "get_categories" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /categories"
  
  # No authorization - open access within VPC
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "get_category" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /categories/{code}"
  
  # No authorization - open access within VPC
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# Sets routes
resource "aws_apigatewayv2_route" "get_sets" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /sets"
  
  # No authorization - open access within VPC
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "get_set" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /sets/{id}"
  
  # No authorization - open access within VPC
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "get_set_by_code" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /sets/code/{code}"
  
  # No authorization - open access within VPC
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# Abstract routes
resource "aws_apigatewayv2_route" "get_abstract" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /papers/{id}/abstract"
  
  # No authorization - open access within VPC
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "put_abstract" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "PUT /papers/{id}/abstract"
  
  # No authorization - open access within VPC
  
  target = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "delete_abstract" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "DELETE /papers/{id}/abstract"
  
  # No authorization - open access within VPC
  
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

# VPC endpoint policy is defined in network.tf

# Outputs for the HTTP API Gateway are defined in outputs.tf
