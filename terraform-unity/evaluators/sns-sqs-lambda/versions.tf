terraform {
  required_version = "~> 1.4.6"

  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = ">=2.4.2"
    }
    aws = {
      source  = "hashicorp/aws"
      version = ">=5.50.0"
    }
    local = {
      source  = "hashicorp/local"
      version = ">=2.5.1"
    }
    null = {
      source  = "hashicorp/null"
      version = ">=3.2.2"
    }
  }
}
