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
    tls = {
      source  = "hashicorp/tls"
      version = ">= 4.0.4"
    }
    local = {
      source  = "hashicorp/local"
      version = ">= 2.0.0"
    }
  }
}

provider "harvester" {
  kubeconfig = "./kubeconfig.yaml"
}
