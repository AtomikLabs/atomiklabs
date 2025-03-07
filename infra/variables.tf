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

variable "email_config" {
  description = "Email configuration"
  type = object({
    recipients = list(string)
  })
}
