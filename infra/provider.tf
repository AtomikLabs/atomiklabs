terraform {
  required_version = ">= 1.10.0"

  backend "s3" {
    key            = "core/terraform.tfstate"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
} 