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

# EBS volume for Neo4j data
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

  # Prevent destruction of the volume
  lifecycle {
    prevent_destroy = true
  }
}

# EC2 instance for Neo4j
resource "aws_instance" "neo4j" {
  ami                    = data.aws_ami.amazon_linux_2.id
  instance_type          = "t3.medium"
  availability_zone      = "${var.region}a"
  subnet_id              = [for s in tolist(data.aws_subnets.default.ids) : s if data.aws_subnet.selected[s].availability_zone == "${var.region}a"][0]
  vpc_security_group_ids = [aws_security_group.neo4j.id]
  key_name               = aws_key_pair.neo4j_ssh.key_name
  
  # Only create 1 instance
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
  chown -R 7474:7474 $MOUNT_POINT
  chmod -R 755 $MOUNT_POINT
fi

# Get Neo4j password from SSM
NEO4J_PASSWORD=$(aws ssm get-parameter --name "/${var.project}/${var.environment}/neo4j/password" --with-decryption --query "Parameter.Value" --output text --region ${var.region})

# Run Neo4j container
docker run -d \
  --name neo4j \
  --restart=always \
  -p 7474:7474 \
  -p 7687:7687 \
  -v $MOUNT_POINT/data:/data \
  -v $MOUNT_POINT/logs:/logs \
  -v $MOUNT_POINT/import:/import \
  -v $MOUNT_POINT/plugins:/plugins \
  -e 'NEO4J_AUTH=neo4j/'"$NEO4J_PASSWORD"'' \
  neo4j:latest
EOF

  tags = merge(
    local.common_tags,
    {
      Name = "${local.resource_prefix}-neo4j-${local.resource_suffix}"
    }
  )

  # Ensure the instance is created before attaching the volume
  depends_on = [aws_ebs_volume.neo4j_data]
}

# Attach the EBS volume to the EC2 instance
resource "aws_volume_attachment" "neo4j_data_attachment" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.neo4j_data.id
  instance_id = aws_instance.neo4j[0].id

  # Skip destroying the attachment when the instance is destroyed
  skip_destroy = true
}

# SSH key pair for Neo4j instance
resource "aws_key_pair" "neo4j_ssh" {
  key_name   = "${local.resource_prefix}-neo4j-key-${local.resource_suffix}"
  public_key = var.laptop_pub_key

  tags = local.common_tags
}

resource "aws_security_group" "neo4j" {
  name        = "${local.resource_prefix}-neo4j-${local.resource_suffix}"
  description = "Security group for Neo4j EC2 instance"
  vpc_id      = data.aws_vpc.default.id

  # SSH access
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH access"
  }

  # Neo4j HTTP access (only accessible via SSH tunnel)
  ingress {
    from_port   = 7474
    to_port     = 7474
    protocol    = "tcp"
    self        = true
    description = "Neo4j HTTP access (via SSH tunnel)"
  }

  # Neo4j Bolt access (only accessible via SSH tunnel)
  ingress {
    from_port   = 7687
    to_port     = 7687
    protocol    = "tcp"
    self        = true
    description = "Neo4j Bolt access (via SSH tunnel)"
  }

  # Allow all outbound traffic
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
