###############################################################################
# main.tf
###############################################################################

# ----------------------
# 0. Local Variables
# ----------------------
locals {
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
# 1. Random ID
###############################################################################
resource "random_id" "secret" {
  byte_length = 4
}

###############################################################################
# 2. Read Your Local Public Keys
###############################################################################
data "local_file" "public_key_rsa" {
  filename = var.keyfile       # e.g. ../keys/id_rsa.pub
}

data "local_file" "public_key_lecturer" {
  filename = var.marker_keyfile  # e.g. ../keys/lecturer_key.pub
}

data "local_file" "ansible_public_key" {
  filename = var.ansible_public  # e.g. ../keys/ansible_ed25519.pub
}

# (Optional) If you need the private key for something else:
data "local_file" "ansible_private_key" {
  filename = var.ansible_private # e.g. ../keys/ansible_ed25519
}

###############################################################################
# 3. Minimal Cloud-Init: Copy Those 3 Public Keys to authorized_keys
###############################################################################
resource "harvester_cloudinit_secret" "cloud_config" {
  name      = "${local.sanitized_username}-cloudinit-${random_id.secret.hex}"
  namespace = var.provider_namespace

  # The simplest approach: just echo each public key into authorized_keys
  user_data = <<-EOF
#cloud-config
runcmd:
  - mkdir -p /home/almalinux/.ssh
  - echo "${data.local_file.public_key_rsa.content}" >> /home/almalinux/.ssh/authorized_keys
  - echo "${data.local_file.public_key_lecturer.content}" >> /home/almalinux/.ssh/authorized_keys
  - echo "${data.local_file.ansible_public_key.content}" >> /home/almalinux/.ssh/authorized_keys
  - chmod 600 /home/almalinux/.ssh/authorized_keys
  - chown -R almalinux:almalinux /home/almalinux/.ssh
EOF
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

  # This references the cloud-init secret
  cloudinit {
    user_data_secret_name = harvester_cloudinit_secret.cloud_config.name
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

  # Instance tags
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

  # Same cloud-init secret as mgmt
  cloudinit {
    user_data_secret_name = harvester_cloudinit_secret.cloud_config.name
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

  # Instance tags
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

  # Same cloud-init secret
  cloudinit {
    user_data_secret_name = harvester_cloudinit_secret.cloud_config.name
  }
}
