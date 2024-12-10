resource "random_id" "secret" {
  byte_length = 4
}

resource "harvester_cloudinit_secret" "cloud_config" {
  name      = "${var.username}-cloudinit-${random_id.secret.hex}"
  namespace = var.provider_namespace
  user_data = <<-EOF
  #cloud-config
  ssh_authorized_keys:
    - ${var.ssh_key}
    - ${var.ssh_key_marker}
  EOF
}

data "harvester_image" "img" {
  name      = var.image_name
  namespace = var.image_namespace
}

# Management VM
resource "harvester_virtualmachine" "mgmt" {
  name                 = "${var.username}-mgmt-${random_id.secret.hex}"
  namespace            = var.provider_namespace
  restart_after_update = true

  description   = "Management Node"
  cpu           = var.mgmt_cpu
  memory        = var.mgmt_memory
  efi           = true
  secure_boot   = false
  run_strategy  = "RerunOnFailure"
  hostname      = "${var.username}-mgmt-${random_id.secret.hex}"
  reserved_memory = "100Mi"
  machine_type  = "q35"

  network_interface {
    name           = "nic-1"
    wait_for_lease = true
    type           = "bridge"
    network_name   = var.network_name
  }

  disk {
    name       = "rootdisk"
    type       = "disk"
    size       = var.mgmt_disk_size
    bus        = "virtio"
    boot_order = 1
    image      = data.harvester_image.img.id
    auto_delete = true
  }

  cloudinit {
    user_data_secret_name = harvester_cloudinit_secret.cloud_config.name
  }
}

# Worker VMs
resource "harvester_virtualmachine" "worker" {
  count               = var.worker_count
  name                = "${var.username}-worker-${count.index + 1}-${random_id.secret.hex}"
  namespace           = var.provider_namespace
  restart_after_update = true

  description   = "Worker Node"
  cpu           = var.worker_cpu
  memory        = var.worker_memory
  efi           = true
  secure_boot   = false
  run_strategy  = "RerunOnFailure"
  hostname      = "${var.username}-worker-${count.index + 1}-${random_id.secret.hex}"
  reserved_memory = "100Mi"
  machine_type  = "q35"

  network_interface {
    name           = "nic-1"
    wait_for_lease = true
    type           = "bridge"
    network_name   = var.network_name
  }

  disk {
    name       = "rootdisk"
    type       = "disk"
    size       = var.worker_disk_size
    bus        = "virtio"
    boot_order = 1
    image      = data.harvester_image.img.id
    auto_delete = true
  }

  cloudinit {
    user_data_secret_name = harvester_cloudinit_secret.cloud_config.name
  }
}

# Storage VM
resource "harvester_virtualmachine" "storage" {
  name                 = "${var.username}-storage-${random_id.secret.hex}"
  namespace            = var.provider_namespace
  restart_after_update = true

  description   = "Storage Node"
  cpu           = var.storage_cpu
  memory        = var.storage_memory
  efi           = true
  secure_boot   = false
  run_strategy  = "RerunOnFailure"
  hostname      = "${var.username}-storage-${random_id.secret.hex}"
  reserved_memory = "100Mi"
  machine_type  = "q35"

  network_interface {
    name           = "nic-1"
    wait_for_lease = true
    type           = "bridge"
    network_name   = var.network_name
  }

  disk {
    name       = "rootdisk"
    type       = "disk"
    size       = var.storage_root_disk_size
    bus        = "virtio"
    boot_order = 1
    image      = data.harvester_image.img.id
    auto_delete = true
  }

  disk {
    name       = "datadisk"
    type       = "disk"
    size       = var.storage_extra_disk_size
    bus        = "virtio"
    auto_delete = true
  }

  cloudinit {
    user_data_secret_name = harvester_cloudinit_secret.cloud_config.name
  }
}
