data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_ebs_volume" "neo4j_data" {
  availability_zone = "${var.region}a"
  size              = 64
  type              = "gp2"
  encrypted         = true

  tags = merge(
    local.common_tags,
    {
      Name = "${local.resource_prefix}-neo4j-data-${local.resource_suffix}"
    }
  )

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_role" "neo4j_instance_role" {
  name = "${local.resource_prefix}-neo4j-role-${substr(local.resource_suffix, 0, 8)}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
  
  tags = local.common_tags
}

resource "aws_iam_role_policy" "neo4j_ssm_access" {
  name = "${local.resource_prefix}-neo4j-ssm-policy-${substr(local.resource_suffix, 0, 8)}"
  role = aws_iam_role.neo4j_instance_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:PutParameter"
        ]
        Effect = "Allow"
        Resource = [
          "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project}/${var.environment}/neo4j/*"
        ]
      }
    ]
  })
}

resource "aws_iam_instance_profile" "neo4j_instance_profile" {
  name = "${local.resource_prefix}-neo4j-profile-${substr(local.resource_suffix, 0, 8)}"
  role = aws_iam_role.neo4j_instance_role.name
  
  tags = local.common_tags
}

resource "aws_instance" "neo4j" {
  ami                         = data.aws_ami.amazon_linux_2.id
  instance_type               = "t3.medium"
  availability_zone           = "${var.region}a"
  subnet_id                   = [for s in tolist(data.aws_subnets.default.ids) : s if data.aws_subnet.selected[s].availability_zone == "${var.region}a"][0]
  vpc_security_group_ids      = [aws_security_group.neo4j.id]
  key_name                    = aws_key_pair.neo4j_ssh.key_name
  iam_instance_profile        = aws_iam_instance_profile.neo4j_instance_profile.name
  associate_public_ip_address = true
  
  count = 1

  root_block_device {
    volume_size = 20
    volume_type = "gp2"
    encrypted   = true
  }

  connection {
    type        = "ssh"
    user        = "ec2-user"
    host        = self.public_ip
    private_key = var.laptop_private_key
  }
  
  provisioner "file" {
    content = templatefile("${path.module}/templates/neo4j-service.sh.tpl", {
      project     = var.project
      environment = var.environment
      region      = var.region
    })
    destination = "/tmp/neo4j-service.sh"
  }
  
  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/neo4j-service.sh",
      "sudo /tmp/neo4j-service.sh"
    ]
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.resource_prefix}-neo4j-${local.resource_suffix}"
    }
  )

  depends_on = [aws_ebs_volume.neo4j_data]
}

resource "aws_volume_attachment" "neo4j_data_attachment" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.neo4j_data.id
  instance_id = aws_instance.neo4j[0].id

  skip_destroy = true
}

resource "aws_key_pair" "neo4j_ssh" {
  key_name   = "${local.resource_prefix}-neo4j-key-${local.resource_suffix}"
  public_key = var.laptop_pub_key

  tags = local.common_tags
}

resource "aws_security_group" "neo4j" {
  name        = "${local.resource_prefix}-neo4j-${local.resource_suffix}"
  description = "Security group for Neo4j EC2 instance"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH access"
  }

  ingress {
    from_port   = 7474
    to_port     = 7474
    protocol    = "tcp"
    self        = true
    description = "Neo4j HTTP access (via SSH tunnel)"
  }

  ingress {
    from_port   = 7687
    to_port     = 7687
    protocol    = "tcp"
    self        = true
    description = "Neo4j Bolt access (via SSH tunnel)"
  }

  ingress {
    from_port       = 7687
    to_port         = 7687
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
    description     = "Neo4j Bolt access from ECS tasks"
  }

  ingress {
    from_port   = 7687
    to_port     = 7687
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.default.cidr_block]
    description = "Neo4j Bolt access from within VPC"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.resource_prefix}-neo4j-sg-${local.resource_suffix}"
    }
  )
}

resource "aws_eip" "neo4j" {
  domain = "vpc"
}

resource "aws_eip_association" "neo4j" {
  instance_id   = aws_instance.neo4j[0].id
  allocation_id = aws_eip.neo4j.id
  
  depends_on = [
    aws_instance.neo4j
  ]
}

resource "aws_ssm_parameter" "neo4j_uri" {
  name        = "/${var.project}/${var.environment}/neo4j/uri"
  description = "URI for connecting to Neo4j"
  type        = "String"
  value       = "bolt://${aws_eip.neo4j.public_ip}:7687"
  overwrite   = true
  
  tags = local.common_tags
}

resource "aws_ssm_parameter" "neo4j_username" {
  name        = "/${var.project}/${var.environment}/neo4j/username"
  description = "Username for connecting to Neo4j"
  type        = "String"
  value       = "neo4j"
  overwrite   = true
  
  tags = local.common_tags
}
