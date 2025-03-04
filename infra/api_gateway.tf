resource "aws_api_gateway_rest_api" "main" {
  name        = "${local.resource_prefix}-api-gateway"
  description = "API Gateway for ${var.project} internal services"

  tags = merge(
    local.common_tags,
    {
      Name = "${local.resource_prefix}-api-gateway"
    }
  )
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${local.resource_prefix}-api-gateway"
  retention_in_days = 30

  tags = merge(
    local.common_tags,
    {
      Name = "${local.resource_prefix}-api-gateway-logs"
    }
  )
}

resource "aws_api_gateway_account" "main" {
  cloudwatch_role_arn = aws_iam_role.api_gateway_cloudwatch.arn
}

resource "aws_iam_role" "api_gateway_cloudwatch" {
  name = "${local.resource_prefix}-api-gw-cloudwatch-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    local.common_tags,
    {
      Name = "${local.resource_prefix}-api-gw-cloudwatch-role"
    }
  )
}

resource "aws_iam_role_policy" "api_gateway_cloudwatch" {
  name = "${local.resource_prefix}-api-gw-cloudwatch-policy"
  role = aws_iam_role.api_gateway_cloudwatch.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams",
          "logs:PutLogEvents",
          "logs:GetLogEvents",
          "logs:FilterLogEvents"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

resource "aws_api_gateway_resource" "dummy" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "dummy"
}

resource "aws_api_gateway_method" "dummy" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.dummy.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "dummy" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.dummy.id
  http_method = aws_api_gateway_method.dummy.http_method
  type        = "MOCK"
  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "dummy" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.dummy.id
  http_method = aws_api_gateway_method.dummy.http_method
  status_code = "200"
  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "dummy" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.dummy.id
  http_method = aws_api_gateway_method.dummy.http_method
  status_code = aws_api_gateway_method_response.dummy.status_code
  response_templates = {
    "application/json" = jsonencode({
      message = "This is a placeholder endpoint"
    })
  }
}

resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.dummy.id,
      aws_api_gateway_method.dummy.id,
      aws_api_gateway_integration.dummy.id
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
  
  depends_on = [
    aws_api_gateway_account.main,
    aws_api_gateway_integration.dummy
  ]
}

resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.environment

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format          = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      integrationLatency = "$context.integrationLatency"
      responseLatency = "$context.responseLatency"
    })
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.resource_prefix}-api-gateway-${var.environment}-stage"
    }
  )
} 