resource "aws_vpc" "app_vpc" {
  cidr_block = var.vpc_cidr
  enable_dns_support = true
  enable_dns_hostnames = true
  tags = {
    Name = "app-vpc-${var.environment}"
  }
}

resource "aws_subnet" "app_subnet" {
  count = length(var.subnet_cidrs)

  vpc_id            = aws_vpc.app_vpc.id
  cidr_block        = var.subnet_cidrs[count.index]
  availability_zone = element(var.availability_zones, count.index)
  map_public_ip_on_launch = true

  tags = {
    Name = "app-subnet-${var.environment}-${count.index}"
  }
}

resource "aws_internet_gateway" "app_igw" {
  vpc_id = aws_vpc.app_vpc.id

  tags = {
    Name = "app-igw-${var.environment}"
  }
}

resource "aws_route_table" "app_rt" {
  vpc_id = aws_vpc.app_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.app_igw.id
  }

  tags = {
    Name = "app-rt-${var.environment}"
  }
}

resource "aws_route_table_association" "app_rta" {
  count = length(var.subnet_cidrs)

  subnet_id      = aws_subnet.app_subnet[count.index].id
  route_table_id = aws_route_table.app_rt.id
}
