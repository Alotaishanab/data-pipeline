######################################
# main.tf - Automated Ansible Key
######################################

locals {
  sanitized_username = replace(replace(var.username, "@", "-"), ".", "-")
}

# Generate the Ansible key pair automatically
resource "tls_private_key" "ansible" {
  algorithm = "ED25519"
}

resource "random_id" "secret" {
  byte_length = 4
}

resource "harvester_cloudinit_secret" "cloud_config" {
  name      = "${local.sanitized_username}-cloudinit-${random_id.secret.hex}"
  namespace = var.provider_namespace

  user_data = <<-EOF
  #cloud-config
  ssh_authorized_keys:
    - ${var.ssh_key}
    - ${var.ssh_key_marker}
    - ${tls_private_key.ansible.public_key_openssh}

  runcmd:
    - yum install -y epel-release
    - yum install -y ansible git
    - git clone https://github.com/Alotaishanab/data-pipeline.git /home/almalinux/data-pipeline

    # Write Ansible private key & add public key to authorized_keys on Host VM
    - mkdir -p /home/almalinux/.ssh
    - echo "${tls_private_key.ansible.private_key_pem}" > /home/almalinux/.ssh/ansible_ed25519
    - chmod 600 /home/almalinux/.ssh/ansible_ed25519
    - echo "${tls_private_key.ansible.public_key_openssh}" >> /home/almalinux/.ssh/authorized_keys
    - chown -R almalinux:almalinux /home/almalinux/.ssh
  EOF
}

data "harvester_image" "img" {
  name      = var.image_name
  namespace = var.image_namespace
}

resource "harvester_virtualmachine" "mgmt" {
  name                 = "${local.sanitized_username}-mgmt-${random_id.secret.hex}"
  namespace            = var.provider_namespace
  restart_after_update = true

  description     = "Management Node"
  cpu             = var.mgmt_cpu
  memory          = var.mgmt_memory
  efi             = true
  secure_boot     = false
  run_strategy    = "RerunOnFailure"
  hostname        = "${local.sanitized_username}-mgmt-${random_id.secret.hex}"
  reserved_memory = "100Mi"
  machine_type    = "q35"

  network_interface {
    name           = "nic-1"
    wait_for_lease = true
    type           = "bridge"
    network_name   = var.network_name
  }

  disk {
    name         = "rootdisk"
    type         = "disk"
    size         = var.mgmt_disk_size
    bus          = "virtio"
    boot_order   = 1
    image        = data.harvester_image.img.id
    auto_delete  = true
  }

  cloudinit {
    user_data_secret_name = harvester_cloudinit_secret.cloud_config.name
  }
}

resource "harvester_virtualmachine" "worker" {
  count                = var.worker_count
  name                 = "${local.sanitized_username}-worker-${count.index + 1}-${random_id.secret.hex}"
  namespace            = var.provider_namespace
  restart_after_update = true

  description     = "Worker Node"
  cpu             = var.worker_cpu
  memory          = var.worker_memory
  efi             = true
  secure_boot     = false
  run_strategy    = "RerunOnFailure"
  hostname        = "${local.sanitized_username}-worker-${count.index + 1}-${random_id.secret.hex}"
  reserved_memory = "100Mi"
  machine_type    = "q35"

  network_interface {
    name           = "nic-1"
    wait_for_lease = true
    type           = "bridge"
    network_name   = var.network_name
  }

  disk {
    name         = "rootdisk"
    type         = "disk"
    size         = var.worker_disk_size
    bus          = "virtio"
    boot_order   = 1
    image        = data.harvester_image.img.id
    auto_delete  = true
  }

  cloudinit {
    user_data_secret_name = harvester_cloudinit_secret.cloud_config.name
  }
}

resource "harvester_virtualmachine" "storage" {
  name                 = "${local.sanitized_username}-storage-${random_id.secret.hex}"
  namespace            = var.provider_namespace
  restart_after_update = true

  description     = "Storage Node"
  cpu             = var.storage_cpu
  memory          = var.storage_memory
  efi             = true
  secure_boot     = false
  run_strategy    = "RerunOnFailure"
  hostname        = "${local.sanitized_username}-storage-${random_id.secret.hex}"
  reserved_memory = "100Mi"
  machine_type    = "q35"

  network_interface {
    name           = "nic-1"
    wait_for_lease = true
    type           = "bridge"
    network_name   = var.network_name
  }

  disk {
    name         = "rootdisk"
    type         = "disk"
    size         = var.storage_root_disk_size
    bus          = "virtio"
    boot_order   = 1
    image        = data.harvester_image.img.id
    auto_delete  = true
  }

  disk {
    name         = "datadisk"
    type         = "disk"
    size         = var.storage_extra_disk_size
    bus          = "virtio"
    auto_delete  = true
  }

  cloudinit {
    user_data_secret_name = harvester_cloudinit_secret.cloud_config.name
  }
}
