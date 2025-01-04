###############################################################################
# main.tf
###############################################################################


# ----------------------
# 0. Local Variables
# ----------------------
locals {
  # This replaces any @ or . in var.username with -
  sanitized_username = replace(replace(var.username, "@", "-"), ".", "-")

  mgmt_vm_tags_full = {
    for key, suffix in var.mgmt_vm_tags :
    key => contains([
      "condenser_ingress_prometheus_hostname",
      "condenser_ingress_grafana_hostname",
      "condenser_ingress_nodeexporter_hostname",
      "condenser_ingress_webserver_hostname"
    ], key) ? "${local.sanitized_username}${suffix}" : suffix
  }

  worker_storage_vm_tags_full = {
    for key, suffix in var.worker_storage_vm_tags :
    key => contains([
      "condenser_ingress_node_hostname"
    ], key) ? "${local.sanitized_username}${suffix}" : suffix
  }
}

###############################################################################
# 1. Random ID (for naming uniqueness)
###############################################################################
resource "random_id" "secret" {
  byte_length = 4
}

###############################################################################
# 2. Generate Ansible Key Pair
###############################################################################
resource "tls_private_key" "ansible" {
  algorithm = "ED25519"
  # This automatically generates:
  #   tls_private_key.ansible.private_key_pem
  #   tls_private_key.ansible.public_key_openssh
}

###############################################################################
# 3. Store the Private Key locally
###############################################################################
# This writes the auto-generated private key to /home/almalinux/.ssh/ansible_ed25519.
resource "local_file" "ansible_private_key" {
  content              = tls_private_key.ansible.private_key_pem
  filename             = "/home/almalinux/.ssh/ansible_ed25519"
  file_permission      = "0600"
  directory_permission = "0700"
}

###############################################################################
# 4. Harvester Image Data
###############################################################################
data "harvester_image" "img" {
  name      = var.image_name
  namespace = var.image_namespace
}

###############################################################################
# 5. Management VM
###############################################################################
resource "harvester_virtualmachine" "mgmt" {
  name                 = "${local.sanitized_username}-mgmt-${random_id.secret.hex}"
  namespace            = var.provider_namespace
  restart_after_update = true

  description      = "Management Node"
  cpu              = var.mgmt_cpu
  memory           = var.mgmt_memory
  efi              = true
  secure_boot      = false
  run_strategy     = "RerunOnFailure"
  hostname         = "${local.sanitized_username}-mgmt-${random_id.secret.hex}"
  reserved_memory  = "100Mi"
  machine_type     = "q35"

  # Instance tags
  tags = local.mgmt_vm_tags_full

  network_interface {
    name           = "nic-1"
    wait_for_lease = true
    type           = "bridge"
    network_name   = var.network_name
  }

  disk {
    name        = "rootdisk"
    type        = "disk"
    size        = var.mgmt_disk_size
    bus         = "virtio"
    boot_order  = 1
    image       = data.harvester_image.img.id
    auto_delete = true
  }

  cloud_init {
    user_data = templatefile(
      "${path.module}/templates/cloud-config.yaml",
      {
        public_key_1 = file(var.keyfile)                  # e.g. ../keys/id_rsa.pub
        public_key_2 = file(var.marker_keyfile)           # e.g. ../keys/lecturer_key.pub
        public_key_3 = tls_private_key.ansible.public_key_openssh
      }
    )
    # If you have network_data, you can do:
    # network_data = file("${path.module}/templates/network-config.yaml")
  }
}

###############################################################################
# 6. Worker VMs
###############################################################################
resource "harvester_virtualmachine" "worker" {
  count                = var.worker_count
  name                 = "${local.sanitized_username}-worker-${count.index + 1}-${random_id.secret.hex}"
  namespace            = var.provider_namespace
  restart_after_update = true

  description      = "Worker Node"
  cpu              = var.worker_cpu
  memory           = var.worker_memory
  efi              = true
  secure_boot      = false
  run_strategy     = "RerunOnFailure"
  hostname         = "${local.sanitized_username}-worker-${count.index + 1}-${random_id.secret.hex}"
  reserved_memory  = "100Mi"
  machine_type     = "q35"

  tags = local.worker_storage_vm_tags_full

  network_interface {
    name           = "nic-1"
    wait_for_lease = true
    type           = "bridge"
    network_name   = var.network_name
  }

  disk {
    name        = "rootdisk"
    type        = "disk"
    size        = var.worker_disk_size
    bus         = "virtio"
    boot_order  = 1
    image       = data.harvester_image.img.id
    auto_delete = true
  }

  cloud_init {
    user_data = templatefile(
      "${path.module}/templates/cloud-config.yaml",
      {
        public_key_1 = file(var.keyfile)
        public_key_2 = file(var.marker_keyfile)
        public_key_3 = tls_private_key.ansible.public_key_openssh
      }
    )
  }
}

###############################################################################
# 7. Storage VM
###############################################################################
resource "harvester_virtualmachine" "storage" {
  name                 = "${local.sanitized_username}-storage-${random_id.secret.hex}"
  namespace            = var.provider_namespace
  restart_after_update = true

  description      = "Storage Node"
  cpu              = var.storage_cpu
  memory           = var.storage_memory
  efi              = true
  secure_boot      = false
  run_strategy     = "RerunOnFailure"
  hostname         = "${local.sanitized_username}-storage-${random_id.secret.hex}"
  reserved_memory  = "100Mi"
  machine_type     = "q35"

  tags = local.worker_storage_vm_tags_full

  network_interface {
    name           = "nic-1"
    wait_for_lease = true
    type           = "bridge"
    network_name   = var.network_name
  }

  disk {
    name        = "rootdisk"
    type        = "disk"
    size        = var.storage_root_disk_size
    bus         = "virtio"
    boot_order  = 1
    image       = data.harvester_image.img.id
    auto_delete = true
  }

  disk {
    name        = "datadisk"
    type        = "disk"
    size        = var.storage_extra_disk_size
    bus         = "virtio"
    auto_delete = true
  }

  cloud_init {
    user_data = templatefile(
      "${path.module}/templates/cloud-config.yaml",
      {
        public_key_1 = file(var.keyfile)
        public_key_2 = file(var.marker_keyfile)
        public_key_3 = tls_private_key.ansible.public_key_openssh
      }
    )
  }
}