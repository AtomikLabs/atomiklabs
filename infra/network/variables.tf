variable "region" {
  type        = string
  description = "AWS region for the VPC"
}

variable "environment" {
  type        = string
  description = "Deployment environment (test, dev, stage, prod)"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for the VPC"
}

variable "subnet_cidrs" {
  type        = list(string)
  description = "List of CIDR blocks for the subnets"
}

variable "availability_zones" {
  type        = list(string)
  description = "List of availability zones in which to create subnets"
}
