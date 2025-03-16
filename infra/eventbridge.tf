resource "aws_iam_role" "eventbridge" {
  name = "${local.resource_prefix}-evb-${substr(local.resource_suffix, 0, 8)}"
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
  name = "${local.resource_prefix}-evb-policy-${substr(local.resource_suffix, 0, 8)}"
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
  name                = "${local.resource_prefix}-daily-${substr(local.resource_suffix, 0, 8)}"
  description         = "Trigger daily processing at 4 AM PT"
  schedule_expression = "cron(0 11 * * ? *)"
}

resource "aws_cloudwatch_event_target" "daily_processor" {
  rule      = aws_cloudwatch_event_rule.daily_processing.name
  target_id = "TriggerDailyProcessing"
  arn       = aws_sfn_state_machine.daily_processor.arn
  role_arn  = aws_iam_role.eventbridge.arn
}

resource "aws_iam_role" "ec2_scheduler" {
  name = "${local.resource_prefix}-ec2-sched-${substr(local.resource_suffix, 0, 8)}"
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

resource "aws_iam_role_policy" "ec2_scheduler" {
  name = "${local.resource_prefix}-ec2-sched-policy-${substr(local.resource_suffix, 0, 8)}"
  role = aws_iam_role.ec2_scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:StartInstances",
          "ec2:StopInstances"
        ]
        Resource = [
          aws_instance.neo4j[0].arn
        ]
      }
    ]
  })
}

resource "aws_cloudwatch_event_rule" "neo4j_start" {
  name                = "${local.resource_prefix}-neo4j-start-${substr(local.resource_suffix, 0, 8)}"
  description         = "Start Neo4j EC2 instance at 1 AM PST"
  schedule_expression = "cron(0 9 * * ? *)" # 1 AM PST = 9 AM UTC
}

resource "aws_cloudwatch_event_target" "neo4j_start" {
  rule      = aws_cloudwatch_event_rule.neo4j_start.name
  target_id = "StartNeo4jInstance"
  arn       = "arn:aws:ssm:${var.region}::automation-definition/AWS-StartEC2Instance"
  role_arn  = aws_iam_role.ec2_scheduler.arn
  
  input = jsonencode({
    InstanceId = [aws_instance.neo4j[0].id]
  })
}

resource "aws_cloudwatch_event_rule" "neo4j_stop" {
  name                = "${local.resource_prefix}-neo4j-stop-${substr(local.resource_suffix, 0, 8)}"
  description         = "Stop Neo4j EC2 instance at 9 AM PST"
  schedule_expression = "cron(0 17 * * ? *)" # 9 AM PST = 17 PM UTC
}

resource "aws_cloudwatch_event_target" "neo4j_stop" {
  rule      = aws_cloudwatch_event_rule.neo4j_stop.name
  target_id = "StopNeo4jInstance"
  arn       = "arn:aws:ssm:${var.region}::automation-definition/AWS-StopEC2Instance"
  role_arn  = aws_iam_role.ec2_scheduler.arn
  
  input = jsonencode({
    InstanceId = [aws_instance.neo4j[0].id]
  })
}
