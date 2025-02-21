resource "aws_iam_role" "eventbridge" {
  name = "${local.resource_prefix}-eventbridge-${local.resource_suffix}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "eventbridge" {
  name = "${local.resource_prefix}-eventbridge-policy-${local.resource_suffix}"
  role = aws_iam_role.eventbridge.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = [
          aws_sfn_state_machine.daily_processor.arn
        ]
      }
    ]
  })
}

resource "aws_cloudwatch_event_rule" "daily_processing" {
  name                = "${local.resource_prefix}-daily-${local.resource_suffix}"
  description         = "Trigger daily processing at 4 AM PT"
  schedule_expression = "cron(0 11 * * ? *)"
}

resource "aws_cloudwatch_event_target" "daily_processor" {
  rule      = aws_cloudwatch_event_rule.daily_processing.name
  target_id = "TriggerDailyProcessing"
  arn       = aws_sfn_state_machine.daily_processor.arn
  role_arn  = aws_iam_role.eventbridge.arn
} 