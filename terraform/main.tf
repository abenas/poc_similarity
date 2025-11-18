terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  # Backend S3 - descomente após criar os recursos com backend-setup.tf
  backend "s3" {
    bucket         = "person-matching-terraform-state-668901804342"
    key            = "person-matching/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "PersonMatching"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
