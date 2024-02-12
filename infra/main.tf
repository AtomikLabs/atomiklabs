terraform {
    backend "s3" {
        bucket          = "atomiklabs-infra-config-bucket"
        key             = "terraform/terraform.state"
        region          = "us-east-1"
        dynamodb_table = "atomiklabs-terraform-locks"
        encrypt         = true
    }
}

module "network" {
  source = "./network"

  region             = var.region
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  subnet_cidrs       = var.subnet_cidrs
  availability_zones = var.availability_zones
}