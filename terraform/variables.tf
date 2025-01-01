###############################################################################
# variables.tf
###############################################################################

variable "provider_endpoint" {
  description = "Endpoint for the Harvester provider"
  type        = string
}

variable "provider_token" {
  description = "Authentication token for the Harvester provider"
  type        = string
  sensitive   = true
}

variable "provider_namespace" {
  description = "Namespace for the Harvester provider"
  type        = string
}

variable "username" {
  description = "User's email address"
  type        = string
}

variable "ssh_key" {
  description = "SSH public key for authentication"
  type        = string
}

variable "ssh_key_marker" {
  description = "SSH key marker"
  type        = string
}

variable "ssh_ansible_private" {
  description = "Ansible private SSH key"
  type        = string
  sensitive   = true
}

variable "ssh_ansible_public" {
  description = "Ansible public SSH key"
  type        = string
}

variable "image_name" {
  description = "Name of the Harvester image"
  type        = string
}

variable "image_namespace" {
  description = "Namespace of the Harvester image"
  type        = string
}

variable "network_name" {
  description = "Name of the network to attach the VMs"
  type        = string
}

# VM Specs Variables
variable "mgmt_cpu" {
  description = "Number of CPUs for Management VM"
  type        = number
}

variable "mgmt_memory" {
  description = "Amount of memory for Management VM"
  type        = string
}

variable "mgmt_disk_size" {
  description = "Disk size for Management VM"
  type        = string
}

variable "worker_count" {
  description = "Number of Worker VMs"
  type        = number
}

variable "worker_cpu" {
  description = "Number of CPUs for Worker VMs"
  type        = number
}

variable "worker_memory" {
  description = "Amount of memory for Worker VMs"
  type        = string
}

variable "worker_disk_size" {
  description = "Disk size for Worker VMs"
  type        = string
}

variable "storage_cpu" {
  description = "Number of CPUs for Storage VM"
  type        = number
}

variable "storage_memory" {
  description = "Amount of memory for Storage VM"
  type        = string
}

variable "storage_root_disk_size" {
  description = "Root disk size for Storage VM"
  type        = string
}

variable "storage_extra_disk_size" {
  description = "Extra disk size for Storage VM"
  type        = string
}

# Instance Tags Variables
variable "mgmt_vm_tags" {
  description = "Instance tags for Management VM"
  type        = map(string)
}

variable "worker_storage_vm_tags" {
  description = "Instance tags for Worker and Storage VMs"
  type        = map(string)
}
