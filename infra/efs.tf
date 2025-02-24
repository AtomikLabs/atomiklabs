resource "aws_efs_file_system" "papers" {
  creation_token = "${local.resource_prefix}-papers-${local.resource_suffix}"
  encrypted      = true
  tags          = local.common_tags
}

resource "aws_efs_access_point" "papers" {
  file_system_id = aws_efs_file_system.papers.id

  posix_user {
    gid = 1000
    uid = 1000
  }

  root_directory {
    path = "/papers"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "755"
    }
  }

  tags = local.common_tags
}

resource "aws_efs_mount_target" "papers" {
  count           = length(data.aws_subnets.default.ids)
  file_system_id  = aws_efs_file_system.papers.id
  subnet_id       = data.aws_subnets.default.ids[count.index]
  security_groups = [aws_security_group.efs.id]
}

resource "aws_security_group" "efs" {
  name        = "${local.resource_prefix}-efs-${local.resource_suffix}"
  description = "Allow NFS traffic for EFS"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id, aws_security_group.lambda_papers.id]
  }

  tags = local.common_tags
} 