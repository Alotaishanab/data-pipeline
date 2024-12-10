variable "provider_endpoint" {
  type        = string
  description = "Harvester API endpoint"
}

variable "provider_token" {
  type        = string
  description = "Harvester API token"
  sensitive   = true
}

variable "provider_namespace" {
  type        = string
  description = "Harvester namespace for VMs"
}

variable "username" {
  type        = string
  description = "Username prefix for naming VMs"
}

variable "ssh_key" {
  type        = string
  description = "SSH public key for VMs"
}

variable "image_name" {
  type        = string
  description = "Actual Harvester image resource name"
}

variable "image_namespace" {
  type        = string
  description = "Namespace where the image resides"
}

variable "network_name" {
  type        = string
  description = "Network name (may include namespace prefix)"
}

# Management VM specs
variable "mgmt_cpu" {
  type    = number
}
variable "mgmt_memory" {
  type    = string
}
variable "mgmt_disk_size" {
  type    = string
}

# Worker specs
variable "worker_count" {
  type = number
}
variable "worker_cpu" {
  type = number
}
variable "worker_memory" {
  type = string
}
variable "worker_disk_size" {
  type = string
}

# Storage VM specs
variable "storage_cpu" {
  type = number
}
variable "storage_memory" {
  type = string
}
variable "storage_root_disk_size" {
  type = string
}
variable "storage_extra_disk_size" {
  type = string
}
