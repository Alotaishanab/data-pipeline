variable "provider_endpoint" {
  type        = string
  description = "Harvester API endpoint (e.g., https://<harvester_api_ip>:6443)"
}

variable "provider_token" {
  type        = string
  description = "Harvester API token"
  sensitive   = true
}

variable "provider_namespace" {
  type        = string
  description = "Harvester namespace"
  default     = "ucabbaa-comp0235-ns"
  # If you have a custom namespace like ucabbaa-comp0235-ns and you have access, use that instead.
}

variable "username" {
  type        = string
  description = "Username prefix for naming VMs"
  default     = "abdullah"
}

variable "ssh_key" {
  type        = string
  description = "SSH public key for VMs"
}

variable "image_name" {
  type        = string
  default     = "harvester-public/almalinux-9.4-20240805"
}

variable "network_name" {
  type        = string
  default     = "ds4eng"
}

# Management VM specs
variable "mgmt_cpu" {
  type    = number
  default = 2
}

variable "mgmt_memory" {
  type    = string
  default = "4Gi"
}

variable "mgmt_disk_size" {
  type    = string
  default = "10Gi"
}

# Worker specs
variable "worker_count" {
  type    = number
  default = 3
}

variable "worker_cpu" {
  type    = number
  default = 4
}

variable "worker_memory" {
  type    = string
  default = "32Gi"
}

variable "worker_disk_size" {
  type    = string
  default = "25Gi"
}
