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
          "ssm:GetParameters"
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
  ami                    = data.aws_ami.amazon_linux_2.id
  instance_type          = "t3.medium"
  availability_zone      = "${var.region}a"
  subnet_id              = [for s in tolist(data.aws_subnets.default.ids) : s if data.aws_subnet.selected[s].availability_zone == "${var.region}a"][0]
  vpc_security_group_ids = [aws_security_group.neo4j.id]
  key_name               = aws_key_pair.neo4j_ssh.key_name
  iam_instance_profile   = aws_iam_instance_profile.neo4j_instance_profile.name
  
  count = 1

  root_block_device {
    volume_size = 20
    volume_type = "gp2"
    encrypted   = true
  }

  user_data = <<-EOF
#!/bin/bash
set -e

# Update system
yum update -y
yum install -y amazon-cloudwatch-agent

# Install Docker
amazon-linux-extras install docker -y
systemctl enable docker
systemctl start docker
usermod -a -G docker ec2-user

# Set up EBS volume
DEVICE_NAME="/dev/sdf"
MOUNT_POINT="/data/neo4j"

# Check if the device exists
if [ -e $DEVICE_NAME ]; then
  # Check if the device is already formatted
  if ! blkid $DEVICE_NAME; then
    # Format the volume if not already formatted
    mkfs -t ext4 $DEVICE_NAME
  fi

  # Create mount point directory
  mkdir -p $MOUNT_POINT

  # Add entry to fstab to mount on boot
  if ! grep -q $DEVICE_NAME /etc/fstab; then
    echo "$DEVICE_NAME $MOUNT_POINT ext4 defaults,nofail 0 2" >> /etc/fstab
  fi

  # Mount the volume
  mount $MOUNT_POINT || mount -a
  
  # Set permissions
  mkdir -p $MOUNT_POINT/data
  mkdir -p $MOUNT_POINT/logs
  mkdir -p $MOUNT_POINT/import
  mkdir -p $MOUNT_POINT/plugins
  chown -R 7474:7474 $MOUNT_POINT || true
  chmod -R 755 $MOUNT_POINT
fi

# Create startup script without variable substitution
cat > /usr/local/bin/start-neo4j.sh << EOF_SCRIPT
#!/bin/bash
set -e

# Wait for docker to be running
while ! systemctl is-active docker; do
  echo "Waiting for Docker to start..."
  sleep 5
done

# Get Neo4j password - fail if not available
echo "Retrieving Neo4j password from SSM Parameter Store..."
PASSWORD_ARG="/${var.project}/${var.environment}/neo4j/password"
NEO4J_PASSWORD=\$(aws ssm get-parameter --name "\$PASSWORD_ARG" --with-decryption --query "Parameter.Value" --output text --region ${var.region})

if [ -z "\$NEO4J_PASSWORD" ]; then
  echo "ERROR: Failed to retrieve Neo4j password from SSM Parameter Store"
  exit 1
fi

# Check if neo4j container exists
if docker ps -a --format '{{.Names}}' | grep -q '^neo4j\$'; then
  # Check if neo4j container is running
  if ! docker ps --format '{{.Names}}' | grep -q '^neo4j\$'; then
    echo "Neo4j container exists but is not running. Starting..."
    docker start neo4j
  else
    echo "Neo4j container is already running."
  fi
else
  echo "Neo4j container does not exist. Creating and starting..."
  # Create and start container
  docker run -d \\
    --name neo4j \\
    --restart=always \\
    -p 7474:7474 \\
    -p 7687:7687 \\
    -v /data/neo4j/data:/data \\
    -v /data/neo4j/logs:/logs \\
    -v /data/neo4j/import:/import \\
    -v /data/neo4j/plugins:/plugins \\
    -e "NEO4J_AUTH=neo4j/\$NEO4J_PASSWORD" \\
    neo4j:latest
fi

# Verify neo4j is running properly
MAX_ATTEMPTS=10
ATTEMPT=0
while [ \$ATTEMPT -lt \$MAX_ATTEMPTS ]; do
  if docker ps --format '{{.Names}}' | grep -q '^neo4j\$'; then
    echo "Neo4j container is running."
    exit 0
  fi
  echo "Waiting for Neo4j container to start... (\$ATTEMPT/\$MAX_ATTEMPTS)"
  ATTEMPT=\$((ATTEMPT+1))
  sleep 5
done

echo "Failed to start Neo4j container after \$MAX_ATTEMPTS attempts."
exit 1
EOF_SCRIPT

chmod +x /usr/local/bin/start-neo4j.sh

# Create systemd service without variable substitution
cat > /etc/systemd/system/neo4j-docker.service << 'EOF_SERVICE'
[Unit]
Description=Neo4j Docker Container
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/start-neo4j.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF_SERVICE

# Enable and start the neo4j service
systemctl daemon-reload
systemctl enable neo4j-docker.service
systemctl start neo4j-docker.service

echo "Neo4j setup complete!"
EOF

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
}
