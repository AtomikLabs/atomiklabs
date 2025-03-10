variable "project" {
  description = "Project name used in resource naming"
  type        = string
  default     = "atomiklabs"
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "resource_uuid" {
  description = "UUID to ensure resource name uniqueness"
  type        = string
}

variable "vpc_cidr_block" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_count" {
  description = "Number of public and private subnets to create (per type)"
  type        = number
  default     = 2
}

variable "private_subnet_offset" {
  description = "CIDR block offset for private subnets"
  type        = number
  default     = 10
}

variable "email_config" {
  description = "Email configuration"
  type = object({
    recipients = list(string)
  })
}
