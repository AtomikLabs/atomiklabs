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

variable "arxiv_config" {
  description = "ArXiv processor configuration"
  type = object({
    categories = list(string)
    back_date  = number
    arxiv_set  = string
  })
  default = {
    categories = ["CL", "CV", "RO", "CR", "AI", "MA", "NE", "IR"]
    back_date  = 1
    arxiv_set  = "cs"
  }
}

variable "email_config" {
  description = "Email configuration"
  type = object({
    recipients = list(string)
  })
}

variable "nvd_api_key" {
  description = "NVD API key"
  type        = string
  sensitive   = true
}

variable "monitored_systems" {
  description = "Systems to monitor for vulnerabilities"
  type = map(object({
    criticality = string
    products = list(string)
  }))
}
