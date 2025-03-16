resource "aws_cloudwatch_log_group" "newsletter_processor" {
  name              = "/ecs/${local.resource_prefix}-newsletter-processor-${local.resource_suffix}"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "arxiv_processor" {
  name              = "/ecs/${local.resource_prefix}-arxiv-processor-${local.resource_suffix}"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "nvd_checker" {
  name              = "/ecs/${local.resource_prefix}-nvd-checker-${local.resource_suffix}"
  retention_in_days = 7
}

# CloudWatch log group for Neo4j EC2 instance
resource "aws_cloudwatch_log_group" "neo4j" {
  name              = "/ec2/${local.resource_prefix}-neo4j-${local.resource_suffix}"
  retention_in_days = 7
}

# CloudWatch dashboard for Neo4j monitoring
resource "aws_cloudwatch_dashboard" "neo4j" {
  dashboard_name = "${local.resource_prefix}-neo4j-dashboard-${local.resource_suffix}"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/EC2", "CPUUtilization", "InstanceId", aws_instance.neo4j[0].id]
          ]
          period = 300
          stat   = "Average"
          region = var.region
          title  = "Neo4j CPU Utilization"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/EC2", "NetworkIn", "InstanceId", aws_instance.neo4j[0].id],
            ["AWS/EC2", "NetworkOut", "InstanceId", aws_instance.neo4j[0].id]
          ]
          period = 300
          stat   = "Average"
          region = var.region
          title  = "Neo4j Network Traffic"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/EC2", "DiskReadBytes", "InstanceId", aws_instance.neo4j[0].id],
            ["AWS/EC2", "DiskWriteBytes", "InstanceId", aws_instance.neo4j[0].id]
          ]
          period = 300
          stat   = "Average"
          region = var.region
          title  = "Neo4j Disk I/O"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/EC2", "StatusCheckFailed", "InstanceId", aws_instance.neo4j[0].id],
            ["AWS/EC2", "StatusCheckFailed_Instance", "InstanceId", aws_instance.neo4j[0].id],
            ["AWS/EC2", "StatusCheckFailed_System", "InstanceId", aws_instance.neo4j[0].id]
          ]
          period = 300
          stat   = "Maximum"
          region = var.region
          title  = "Neo4j Status Checks"
        }
      }
    ]
  })
}

# CloudWatch alarm for Neo4j high CPU
resource "aws_cloudwatch_metric_alarm" "neo4j_cpu" {
  alarm_name          = "${local.resource_prefix}-neo4j-high-cpu-${local.resource_suffix}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "This metric monitors Neo4j EC2 CPU utilization"
  
  dimensions = {
    InstanceId = aws_instance.neo4j[0].id
  }
}

# DLM lifecycle policy for weekly EBS snapshots
resource "aws_dlm_lifecycle_policy" "neo4j_ebs_snapshot" {
  description        = "Weekly EBS snapshot policy for Neo4j data volume"
  execution_role_arn = aws_iam_role.dlm_lifecycle_role.arn
  state              = "ENABLED"

  policy_details {
    resource_types = ["VOLUME"]

    schedule {
      name = "Weekly Snapshots"
      
      create_rule {
        interval      = 24
        interval_unit = "HOURS"
        times         = ["23:45"]
      }
      
      retain_rule {
        count = 7
      }
      
      tags_to_add = {
        SnapshotCreator = "DLM"
      }
      
      copy_tags = true
    }

    target_tags = {
      Name = "${local.resource_prefix}-neo4j-data-${local.resource_suffix}"
    }
  }

  tags = local.common_tags
}

# IAM role for DLM lifecycle policy
resource "aws_iam_role" "dlm_lifecycle_role" {
  name = "${local.resource_prefix}-dlm-role-${substr(local.resource_suffix, 0, 8)}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "dlm.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "dlm_lifecycle" {
  name = "${local.resource_prefix}-dlm-policy-${substr(local.resource_suffix, 0, 8)}"
  role = aws_iam_role.dlm_lifecycle_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateSnapshot",
          "ec2:DeleteSnapshot",
          "ec2:DescribeVolumes",
          "ec2:DescribeSnapshots"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateTags"
        ]
        Resource = "arn:aws:ec2:*::snapshot/*"
      }
    ]
  })
}
