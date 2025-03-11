resource "aws_api_gateway_rest_api" "main" {
  name        = "${local.resource_prefix}-api-gateway"
  description = "API Gateway for ${var.project} internal services"

  # Configure as private API Gateway (only accessible via VPC endpoint)
  endpoint_configuration {
    types = ["PRIVATE"]
    vpc_endpoint_ids = [aws_vpc_endpoint.api_gateway.id]
  }

  # Improved resource policy with more permissive permissions to allow ECS tasks
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Allow access from within our VPC with specific resource scope
      {
        Effect = "Allow"
        Principal = "*"
        Action = "execute-api:Invoke"
        Resource = "arn:aws:execute-api:${var.region}:${data.aws_caller_identity.current.account_id}:*/*"
        Condition = {
          StringEquals = {
            "aws:SourceVpc": data.aws_vpc.default.id
          }
        }
      },
      # Allow access from the VPC endpoint with specific resource scope
      {
        Effect = "Allow"
        Principal = "*"
        Action = "execute-api:Invoke"
        Resource = "arn:aws:execute-api:${var.region}:${data.aws_caller_identity.current.account_id}:*/*"
        Condition = {
          StringEquals = {
            "aws:SourceVpce": aws_vpc_endpoint.api_gateway.id
          }
        }
      },
      # Allow access from specific IAM roles with specific resource scope
      # This statement allows the ECS task role to access the API Gateway
      # without requiring a specific source VPC or VPC endpoint
      {
        Effect = "Allow"
        Principal = {
          AWS = [
            aws_iam_role.ecs_task_role.arn,
            aws_iam_role.lambda_arxiv_api.arn
          ]
        }
        Action = "execute-api:Invoke"
        Resource = "arn:aws:execute-api:${var.region}:${data.aws_caller_identity.current.account_id}:*/*"
      }
    ]
  })

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

# API resources for the arXiv data layer

# Papers resource
resource "aws_api_gateway_resource" "papers" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "papers"
}

resource "aws_api_gateway_resource" "paper" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.papers.id
  path_part   = "{id}"
}

# Authors resource
resource "aws_api_gateway_resource" "authors" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "authors"
}

resource "aws_api_gateway_resource" "author" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.authors.id
  path_part   = "{id}"
}

resource "aws_api_gateway_resource" "paper_authors" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.paper.id
  path_part   = "authors"
}

# Categories resource
resource "aws_api_gateway_resource" "categories" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "categories"
}

resource "aws_api_gateway_resource" "category" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.categories.id
  path_part   = "{code}"
}

# Sets resource
resource "aws_api_gateway_resource" "sets" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "sets"
}

resource "aws_api_gateway_resource" "set" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.sets.id
  path_part   = "{id}"
}

resource "aws_api_gateway_resource" "sets_code" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.sets.id
  path_part   = "code"
}

resource "aws_api_gateway_resource" "set_code" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.sets_code.id
  path_part   = "{code}"
}

# API methods for data layer API
# Papers

resource "aws_api_gateway_method" "get_papers" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.papers.id
  http_method   = "GET"
  authorization = "AWS_IAM"
}

resource "aws_api_gateway_integration" "get_papers" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.papers.id
  http_method             = aws_api_gateway_method.get_papers.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.arxiv_api.invoke_arn
}

resource "aws_api_gateway_method" "get_paper" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.paper.id
  http_method   = "GET"
  authorization = "AWS_IAM"
  request_parameters = {
    "method.request.path.id" = true
  }
}

resource "aws_api_gateway_integration" "get_paper" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.paper.id
  http_method             = aws_api_gateway_method.get_paper.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.arxiv_api.invoke_arn
}

# Authors
resource "aws_api_gateway_method" "get_authors" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.authors.id
  http_method   = "GET"
  authorization = "AWS_IAM"
}

resource "aws_api_gateway_integration" "get_authors" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.authors.id
  http_method             = aws_api_gateway_method.get_authors.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.arxiv_api.invoke_arn
}

resource "aws_api_gateway_method" "get_author" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.author.id
  http_method   = "GET"
  authorization = "AWS_IAM"
  request_parameters = {
    "method.request.path.id" = true
  }
}

resource "aws_api_gateway_integration" "get_author" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.author.id
  http_method             = aws_api_gateway_method.get_author.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.arxiv_api.invoke_arn
}

resource "aws_api_gateway_method" "get_paper_authors" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.paper_authors.id
  http_method   = "GET"
  authorization = "AWS_IAM"
  request_parameters = {
    "method.request.path.paper_id" = true
  }
}

resource "aws_api_gateway_integration" "get_paper_authors" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.paper_authors.id
  http_method             = aws_api_gateway_method.get_paper_authors.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.arxiv_api.invoke_arn
}

# Categories
resource "aws_api_gateway_method" "get_categories" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.categories.id
  http_method   = "GET"
  authorization = "AWS_IAM"
}

resource "aws_api_gateway_integration" "get_categories" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.categories.id
  http_method             = aws_api_gateway_method.get_categories.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.arxiv_api.invoke_arn
}

resource "aws_api_gateway_method" "get_category" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.category.id
  http_method   = "GET"
  authorization = "AWS_IAM"
  request_parameters = {
    "method.request.path.id" = true
  }
}

resource "aws_api_gateway_integration" "get_category" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.category.id
  http_method             = aws_api_gateway_method.get_category.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.arxiv_api.invoke_arn
}

# Sets
resource "aws_api_gateway_method" "get_sets" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.sets.id
  http_method   = "GET"
  authorization = "AWS_IAM"
}

resource "aws_api_gateway_integration" "get_sets" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.sets.id
  http_method             = aws_api_gateway_method.get_sets.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.arxiv_api.invoke_arn
}

resource "aws_api_gateway_method" "get_set" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.set.id
  http_method   = "GET"
  authorization = "AWS_IAM"
  request_parameters = {
    "method.request.path.id" = true
  }
}

resource "aws_api_gateway_integration" "get_set" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.set.id
  http_method             = aws_api_gateway_method.get_set.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.arxiv_api.invoke_arn
}

resource "aws_api_gateway_method" "get_set_by_code" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.set_code.id
  http_method   = "GET"
  authorization = "AWS_IAM"
  request_parameters = {
    "method.request.path.code" = true
  }
}

resource "aws_api_gateway_integration" "get_set_by_code" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.set_code.id
  http_method             = aws_api_gateway_method.get_set_by_code.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.arxiv_api.invoke_arn
}

# Paper abstracts resource
resource "aws_api_gateway_resource" "paper_abstract" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.paper.id
  path_part   = "abstract"
}

# Abstract API methods
resource "aws_api_gateway_method" "get_abstract" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.paper_abstract.id
  http_method   = "GET"
  authorization = "AWS_IAM"
  request_parameters = {
    "method.request.path.paper_id" = true
  }
}

resource "aws_api_gateway_integration" "get_abstract" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.paper_abstract.id
  http_method             = aws_api_gateway_method.get_abstract.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.arxiv_api.invoke_arn
}

resource "aws_api_gateway_method" "put_abstract" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.paper_abstract.id
  http_method   = "PUT"
  authorization = "AWS_IAM"
  request_parameters = {
    "method.request.path.paper_id" = true
  }
}

resource "aws_api_gateway_integration" "put_abstract" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.paper_abstract.id
  http_method             = aws_api_gateway_method.put_abstract.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.arxiv_api.invoke_arn
}

resource "aws_api_gateway_method" "delete_abstract" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.paper_abstract.id
  http_method   = "DELETE"
  authorization = "AWS_IAM"
  request_parameters = {
    "method.request.path.paper_id" = true
  }
}

resource "aws_api_gateway_integration" "delete_abstract" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.paper_abstract.id
  http_method             = aws_api_gateway_method.delete_abstract.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.arxiv_api.invoke_arn
}

# Update the API Gateway deployment to include the new endpoints
resource "aws_lambda_permission" "api_gateway_arxiv_api" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.arxiv_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# Update triggers for redeployment
resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.dummy.id,
      aws_api_gateway_method.dummy.id,
      aws_api_gateway_integration.dummy.id,
      # Include new resources
      aws_api_gateway_resource.papers.id,
      aws_api_gateway_resource.paper.id,
      aws_api_gateway_resource.authors.id,
      aws_api_gateway_resource.author.id,
      aws_api_gateway_resource.paper_authors.id,
      aws_api_gateway_resource.categories.id,
      aws_api_gateway_resource.category.id,
      aws_api_gateway_resource.sets.id,
      aws_api_gateway_resource.set.id,
      aws_api_gateway_resource.sets_code.id,
      aws_api_gateway_resource.set_code.id,
      # Include new methods
      aws_api_gateway_method.get_papers.id,
      aws_api_gateway_method.get_paper.id,
      aws_api_gateway_method.get_authors.id,
      aws_api_gateway_method.get_author.id,
      aws_api_gateway_method.get_paper_authors.id,
      aws_api_gateway_method.get_categories.id,
      aws_api_gateway_method.get_category.id,
      aws_api_gateway_method.get_sets.id,
      aws_api_gateway_method.get_set.id,
      aws_api_gateway_method.get_set_by_code.id,
      # Include new integrations
      aws_api_gateway_integration.get_papers.id,
      aws_api_gateway_integration.get_paper.id,
      aws_api_gateway_integration.get_authors.id,
      aws_api_gateway_integration.get_author.id,
      aws_api_gateway_integration.get_paper_authors.id,
      aws_api_gateway_integration.get_categories.id,
      aws_api_gateway_integration.get_category.id,
      aws_api_gateway_integration.get_sets.id,
      aws_api_gateway_integration.get_set.id,
      aws_api_gateway_integration.get_set_by_code.id,
      # Include abstract resources
      aws_api_gateway_resource.paper_abstract.id,
      aws_api_gateway_method.get_abstract.id,
      aws_api_gateway_method.put_abstract.id,
      aws_api_gateway_method.delete_abstract.id,
      aws_api_gateway_integration.get_abstract.id,
      aws_api_gateway_integration.put_abstract.id,
      aws_api_gateway_integration.delete_abstract.id
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
  
  depends_on = [
    aws_api_gateway_account.main,
    aws_api_gateway_integration.dummy,
    # Include new integrations
    aws_api_gateway_integration.get_papers,
    aws_api_gateway_integration.get_paper,
    aws_api_gateway_integration.get_authors,
    aws_api_gateway_integration.get_author,
    aws_api_gateway_integration.get_paper_authors,
    aws_api_gateway_integration.get_categories,
    aws_api_gateway_integration.get_category,
    aws_api_gateway_integration.get_sets,
    aws_api_gateway_integration.get_set,
    aws_api_gateway_integration.get_set_by_code,
    # Include abstract integrations
    aws_api_gateway_integration.get_abstract,
    aws_api_gateway_integration.put_abstract,
    aws_api_gateway_integration.delete_abstract
  ]
}

resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.environment
  
  # Enable X-Ray tracing
  xray_tracing_enabled = true

  # Add cache configuration
  cache_cluster_enabled = false
  
  # Configure stage variables
  variables = {
    deployed_at = timestamp()
  }
  
  # Set stage settings
  cache_cluster_size    = null  # Set to 0.5, 1.6, 13.5, etc. if cache_cluster_enabled = true
  documentation_version = null  # Set if using API documentation

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
      errorMessage   = "$context.error.message"  # Added error message
      errorType      = "$context.error.responseType"  # Added error type
      authorizationType = "$context.authorizer.type"  # Added authorizer information
    })
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.resource_prefix}-api-gateway-${var.environment}-stage"
    }
  )
}

# Add method settings to enable detailed metrics
resource "aws_api_gateway_method_settings" "all" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  stage_name  = aws_api_gateway_stage.main.stage_name
  method_path = "*/*"

  settings {
    metrics_enabled        = true
    logging_level          = "INFO"  # Set to ERROR, INFO, or DEBUG
    data_trace_enabled     = true    # Enable request/response logging
    throttling_rate_limit  = 100     # Limit the number of requests per second
    throttling_burst_limit = 50      # Limit the number of concurrent requests
    caching_enabled        = false   # Enable caching
  }
} 