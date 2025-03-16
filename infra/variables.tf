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
  description = "ArXiv processor configuration for multiple sets"
  type = object({
    sets = map(object({
      categories = list(string)
      back_date = number
    }))
    default_back_date = number
  })
  
  default = {
    sets = {
      cs = {
        categories = ["AI", "CL", "CR", "CV", "DB", "DS", "IT", "RO", "SC"]
        back_date = 3
      },
      math = {
        categories = ["DS", "GR", "PR"]
        back_date = 3
      }
    }
    default_back_date = 1
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

variable "laptop_pub_key" {
  description = "Public SSH key for accessing the Neo4j EC2 instance"
  type        = string
  sensitive   = true
}

variable "neo4j_password" {
  description = "Initial password for Neo4j database"
  type        = string
  sensitive   = true
  default     = "neo4j"
}
