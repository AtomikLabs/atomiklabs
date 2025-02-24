resource "aws_efs_file_system" "sqlite_storage" {
  creation_token = "${local.resource_prefix}-sqlite-${local.resource_suffix}"
  encrypted      = true

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-sqlite-${local.resource_suffix}"
  })
}

resource "aws_efs_mount_target" "sqlite_storage" {
  for_each = toset(data.aws_subnets.default.ids)

  file_system_id  = aws_efs_file_system.sqlite_storage.id
  subnet_id       = each.value
  security_groups = [aws_security_group.efs.id]
}

resource "aws_efs_access_point" "sqlite_data" {
  file_system_id = aws_efs_file_system.sqlite_storage.id

  root_directory {
    path = "/sqlite"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "755"
    }
  }

  posix_user {
    gid = 1000
    uid = 1000
  }

  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-sqlite-ap-${local.resource_suffix}"
  })
}

# Output the EFS DNS name and Access Point ID for use in other configurations
output "efs_dns_name" {
  description = "DNS name of the EFS file system"
  value       = aws_efs_file_system.sqlite_storage.dns_name
}

output "efs_access_point_id" {
  description = "ID of the EFS access point"
  value       = aws_efs_access_point.sqlite_data.id
}
