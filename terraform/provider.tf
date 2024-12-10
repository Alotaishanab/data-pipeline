terraform {
  required_version = ">= 1.0.0"
  required_providers {
    harvester = {
      source  = "harvester/harvester"
      version = ">= 0.2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">=3.1.0"
    }
  }
}

provider "harvester" {
  endpoint  = var.provider_endpoint
  token     = var.provider_token
  namespace = var.provider_namespace
}
