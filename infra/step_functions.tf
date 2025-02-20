resource "aws_iam_role" "step_functions" {
  name = "${local.resource_prefix}-sfn-${local.resource_suffix}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "step_functions" {
  name = "${local.resource_prefix}-step-functions-policy-${local.resource_suffix}"
  role = aws_iam_role.step_functions.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecs:RunTask",
          "ecs:StopTask",
          "ecs:DescribeTasks"
        ]
        Resource = [
          aws_ecs_task_definition.arxiv_processor.arn,
          replace(aws_ecs_task_definition.arxiv_processor.arn, "/:\\d+$/", ":*")
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = [
          aws_iam_role.ecs_task_role.arn,
          aws_iam_role.ecs_execution_role.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "events:PutTargets",
          "events:PutRule",
          "events:DescribeRule"
        ]
        Resource = [
          "arn:aws:events:${var.region}:${data.aws_caller_identity.current.account_id}:rule/StepFunctionsGetEventsForECSTaskRule"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_lambda_function.mailer.arn
        ]
      }
    ]
  })
}

resource "aws_sfn_state_machine" "arxiv_processor" {
  name     = "${local.resource_prefix}-arxiv-processor-${local.resource_suffix}"
  role_arn = aws_iam_role.step_functions.arn

  definition = jsonencode({
    Comment = "ArXiv paper processing workflow"
    StartAt = "Process Papers"
    States = {
      "Process Papers" = {
        Type = "Task"
        Resource = "arn:aws:states:::ecs:runTask.sync"
        Parameters = {
          LaunchType = "FARGATE"
          Cluster = aws_ecs_cluster.arxiv.arn
          TaskDefinition = aws_ecs_task_definition.arxiv_processor.arn
          NetworkConfiguration = {
            AwsvpcConfiguration = {
              Subnets = data.aws_subnets.default.ids
              SecurityGroups = [aws_security_group.ecs_tasks.id]
              AssignPublicIp = "ENABLED"
            }
          }
        }
        Next = "Send Email"
      },
      "Send Email" = {
        Type = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.mailer.arn
          Payload = {
            "id": "daily-summary",
            "date.$": "$$.State.EnteredTime"
          }
        }
        ResultPath = "$.taskresult"
        End = true
      }
    }
  })
}
