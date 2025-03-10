# Custom VPC for the application
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr_block
  enable_dns_support   = true
  enable_dns_hostnames = true
  instance_tenancy     = "default"
  
  # Enable IPv6 if needed in the future
  assign_generated_ipv6_cidr_block = false
  
  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-vpc"
    Environment = var.environment
    ManagedBy = "terraform"
  })
}

# Enable VPC Flow Logs for security monitoring
resource "aws_flow_log" "main" {
  log_destination      = aws_cloudwatch_log_group.vpc_flow_log.arn
  log_destination_type = "cloud-watch-logs"
  traffic_type         = "ALL"
  vpc_id               = aws_vpc.main.id
  iam_role_arn         = aws_iam_role.vpc_flow_log.arn
  
  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-vpc-flow-log"
  })
}

resource "aws_cloudwatch_log_group" "vpc_flow_log" {
  name              = "/aws/vpc/flow-log/${local.resource_prefix}-vpc"
  retention_in_days = 30
  
  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-vpc-flow-log"
  })
}

resource "aws_iam_role" "vpc_flow_log" {
  name = "${local.resource_prefix}-vpc-flow-log-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-vpc-flow-log-role"
  })
}

resource "aws_iam_role_policy" "vpc_flow_log" {
  name = "${local.resource_prefix}-vpc-flow-log-policy"
  role = aws_iam_role.vpc_flow_log.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# Internet Gateway - allows communication between VPC and the internet
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  
  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-igw"
    Environment = var.environment
    ManagedBy = "terraform"
  })
}

# Elastic IP for NAT Gateway - static public IP address
resource "aws_eip" "nat" {
  count = var.subnet_count > 0 ? 1 : 0
  domain = "vpc"
  
  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-nat-eip"
    Environment = var.environment
    ManagedBy = "terraform"
  })
  
  # Ensure the Internet Gateway exists before creating the EIP
  depends_on = [aws_internet_gateway.main]
}

# NAT Gateway - allows private subnet resources to access the internet
resource "aws_nat_gateway" "main" {
  count = var.subnet_count > 0 ? 1 : 0
  
  # Allocate the Elastic IP to the NAT Gateway
  allocation_id = aws_eip.nat[0].id
  
  # Place the NAT Gateway in the first public subnet
  # This is a common pattern - one NAT Gateway serving multiple private subnets
  subnet_id = aws_subnet.public[0].id
  
  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-nat-gateway"
    Environment = var.environment
    ManagedBy = "terraform"
  })
  
  # Ensure the Internet Gateway exists before creating the NAT Gateway
  # This is important because the NAT Gateway needs internet access
  depends_on = [aws_internet_gateway.main]
}

# Public Route Table - for subnets that need direct internet access
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  
  # Route all internet-bound traffic through the Internet Gateway
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-public-rt"
    Type = "Public"
    Environment = var.environment
    ManagedBy = "terraform"
  })
}

# Private Route Table - for subnets that need indirect internet access via NAT
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  
  # Only create the route if we have a NAT Gateway
  dynamic "route" {
    for_each = var.subnet_count > 0 ? [1] : []
    content {
      # Route all internet-bound traffic through the NAT Gateway
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = aws_nat_gateway.main[0].id
    }
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-private-rt"
    Type = "Private"
    Environment = var.environment
    ManagedBy = "terraform"
  })
}

# Associate public subnets with the public route table
resource "aws_route_table_association" "public" {
  count          = var.subnet_count
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Associate private subnets with the private route table
resource "aws_route_table_association" "private" {
  count          = var.subnet_count
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# Data source for all route tables in the VPC
data "aws_route_tables" "all" {
  vpc_id = aws_vpc.main.id
  
  depends_on = [
    aws_route_table.public,
    aws_route_table.private,
    aws_route_table_association.public,
    aws_route_table_association.private
  ]
}

# Security group for VPC endpoints - restricts access to only necessary sources
resource "aws_security_group" "vpc_endpoints" {
  name        = "${local.resource_prefix}-vpc-endpoints-sg-${local.resource_suffix}"
  description = "Security group for VPC endpoints with restricted access"
  vpc_id      = aws_vpc.main.id

  # Allow HTTPS inbound from ECS tasks
  ingress {
    description     = "HTTPS from ECS tasks"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  # Allow HTTPS inbound from Lambda functions
  ingress {
    description     = "HTTPS from Lambda functions"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id]
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-vpc-endpoints-sg"
    Environment = var.environment
    ManagedBy = "terraform"
  })
}

# Get available availability zones in the region
data "aws_availability_zones" "available" {
  state = "available"
}

# Public subnets - for resources that need direct internet access
# These subnets will host NAT Gateways and resources that need public IPs
resource "aws_subnet" "public" {
  count             = var.subnet_count
  vpc_id            = aws_vpc.main.id
  # Use the newbits parameter to create the appropriate sized subnet from the VPC CIDR
  # For a /16 VPC CIDR, this creates /24 subnets (256 IPs each)
  cidr_block        = cidrsubnet(var.vpc_cidr_block, 8, count.index)
  # Use modulo to cycle through available AZs if we need more subnets than AZs
  availability_zone = data.aws_availability_zones.available.names[count.index % length(data.aws_availability_zones.available.names)]
  
  # Enable auto-assign public IP for resources in public subnets
  # This is required for instances that need direct internet access
  map_public_ip_on_launch = true
  
  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-public-subnet-${count.index + 1}"
    Type = "Public"
    Environment = var.environment
    ManagedBy = "terraform"
    "kubernetes.io/role/elb" = "1"  # Tag for AWS Load Balancer Controller if used
  })
}

# Private subnets - for resources that should not be directly accessible from the internet
# These subnets will host application servers, databases, and other internal resources
resource "aws_subnet" "private" {
  count             = var.subnet_count
  vpc_id            = aws_vpc.main.id
  # Use an offset to ensure private subnet CIDRs don't overlap with public ones
  cidr_block        = cidrsubnet(var.vpc_cidr_block, 8, count.index + var.private_subnet_offset)
  # Use modulo to cycle through available AZs if we need more subnets than AZs
  availability_zone = data.aws_availability_zones.available.names[count.index % length(data.aws_availability_zones.available.names)]
  
  # Disable auto-assign public IP for resources in private subnets
  # Resources in these subnets will use NAT Gateway for outbound internet access
  map_public_ip_on_launch = false
  
  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-private-subnet-${count.index + 1}"
    Type = "Private"
    Environment = var.environment
    ManagedBy = "terraform"
    "kubernetes.io/role/internal-elb" = "1"  # Tag for AWS Load Balancer Controller if used
  })
}

# Create data sources for the new subnets to be used by other resources
data "aws_subnets" "public" {
  filter {
    name   = "vpc-id"
    values = [aws_vpc.main.id]
  }
  
  filter {
    name   = "tag:Type"
    values = ["Public"]
  }
  
  depends_on = [aws_subnet.public]
}

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [aws_vpc.main.id]
  }
  
  filter {
    name   = "tag:Type"
    values = ["Private"]
  }
  
  depends_on = [aws_subnet.private]
}

# Keep the data source but reference our custom VPC instead of the default one
data "aws_vpc" "default" {
  id = aws_vpc.main.id
}

# Update the default subnets data source to include both public and private subnets
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  
  depends_on = [aws_subnet.public, aws_subnet.private]
}

# Update the default route tables data source to use the new data source
data "aws_route_tables" "default" {
  vpc_id = data.aws_vpc.default.id
  
  depends_on = [
    aws_route_table.public,
    aws_route_table.private,
    aws_route_table_association.public,
    aws_route_table_association.private
  ]
}

resource "aws_security_group" "ecs_tasks" {
  name        = "${local.resource_prefix}-ecs-tasks-${local.resource_suffix}"
  description = "Allow outbound traffic for ECS tasks"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]
  
  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-s3-endpoint"
    Environment = var.environment
    ManagedBy = "terraform"
  })
}

resource "aws_vpc_endpoint" "ssm" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.ssm"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = data.aws_subnets.private.ids
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true
  
  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-ssm-endpoint"
    Environment = var.environment
    ManagedBy = "terraform"
  })
}

# SES VPC Endpoint (Interface type)
resource "aws_vpc_endpoint" "ses" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.email-smtp"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = data.aws_subnets.private.ids
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true
  
  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-ses-endpoint"
    Environment = var.environment
    ManagedBy = "terraform"
  })
}

# Lambda VPC Endpoint (Interface type)
resource "aws_vpc_endpoint" "lambda" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.lambda"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = data.aws_subnets.private.ids
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true
  
  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-lambda-endpoint"
    Environment = var.environment
    ManagedBy = "terraform"
  })
}

# API Gateway VPC Endpoint (Interface type)
resource "aws_vpc_endpoint" "api_gateway" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.execute-api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = data.aws_subnets.private.ids
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true
  
  # Use a wildcard for the API Gateway ID to break the circular dependency
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = "execute-api:Invoke"
        Resource  = "arn:aws:execute-api:${var.region}:${data.aws_caller_identity.current.account_id}:*/*"
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Name = "${local.resource_prefix}-api-gateway-endpoint"
    Environment = var.environment
    ManagedBy = "terraform"
  })
} 