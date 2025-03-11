resource "aws_cloudwatch_log_group" "arxiv_processor" {
  name              = "/ecs/${local.resource_prefix}-arxiv-processor-${local.resource_suffix}"
  retention_in_days = 7
}

# CloudWatch alarms for HTTP API Gateway
resource "aws_cloudwatch_metric_alarm" "api_gateway_5xx" {
  alarm_name          = "${local.resource_prefix}-api-gateway-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "5xx"  # Note: HTTP API uses lowercase metric names
  namespace           = "AWS/ApiGateway"
  period              = "60"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This alarm monitors HTTP API Gateway 5XX errors"
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    ApiId  = aws_apigatewayv2_api.http_api.id
    Stage  = aws_apigatewayv2_stage.dev.name
  }
}

# CloudWatch alarm for Lambda errors
resource "aws_cloudwatch_metric_alarm" "lambda_api_errors" {
  alarm_name          = "${local.resource_prefix}-lambda-api-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "2"
  alarm_description   = "This alarm monitors Lambda API errors"
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    FunctionName = aws_lambda_function.arxiv_api.function_name
  }
}
