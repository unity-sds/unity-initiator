terraform {
  required_version = "~> 1.8.2"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">=5.50.0"
    }
    local = {
      source  = "hashicorp/local"
      version = ">=2.5.1"
    }
  }
}