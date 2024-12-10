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
  EOF
}

resource "harvester_virtualmachine" "mgmt" {
  name                 = "${var.username}-mgmt-${random_id.secret.hex}"
  namespace            = var.provider_namespace
  run_strategy         = "RerunOnFailure"
  cpu                  = var.mgmt_cpu
  memory               = var.mgmt_memory
  efi                  = true
  secure_boot          = false

  hostname     = "${var.username}-mgmt-${random_id.secret.hex}"
  machine_type = "q35"

  network_interface {
    name           = "nic-1"
    wait_for_lease = true
    type           = "bridge"
    network_name   = var.network_name
  }

  disk {
    name        = "rootdisk"
    size        = var.mgmt_disk_size
    type        = "disk"
    image       = var.image_name
    bus         = "virtio"
    boot_order  = 1
    auto_delete = true
  }

  cloudinit {
    user_data_secret_name = harvester_cloudinit_secret.cloud_config.name
  }
}

resource "harvester_virtualmachine" "worker" {
  count               = var.worker_count
  name                = "${var.username}-worker-${count.index + 1}-${random_id.secret.hex}"
  namespace           = var.provider_namespace
  run_strategy         = "RerunOnFailure"
  cpu                  = var.worker_cpu
  memory               = var.worker_memory
  efi                  = true
  secure_boot          = false
  hostname             = "${var.username}-worker-${count.index + 1}-${random_id.secret.hex}"
  machine_type         = "q35"

  network_interface {
    name           = "nic-1"
    wait_for_lease = true
    type           = "bridge"
    network_name   = var.network_name
  }

  disk {
    name        = "rootdisk"
    size        = var.worker_disk_size
    type        = "disk"
    image       = var.image_name
    bus         = "virtio"
    boot_order  = 1
    auto_delete = true
  }

  cloudinit {
    user_data_secret_name = harvester_cloudinit_secret.cloud_config.name
  }
}
