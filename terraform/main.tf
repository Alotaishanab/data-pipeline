resource "random_id" "secret" {
  byte_length = 4
}

locals {
  ssh_key      = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDEGYMIHQdWQv/nwFf7zN2Pue60T+Outmr202vz3/DPAA+ufAWfo9FRw4r4dR44jFZpqmwIm2GCIH/JmB9/ETJsYgOJLBhxC+1Dea75jsQh7deYIcyfJQKJpnb0S5FJbg2+6H3jfGLj/MvoU/tVVqz2lNOmpApSj7B0Npo/qkea/3kzXhFz8Bhu4K1Glr0bh1d4YYLQ20SrSpFR+uGcwkKuOBMX12T25tNPADQ+Wi/nVK7jD9124oqcpgCGLDHWpSULX/AYCxCqMQOih3Kb2B6x7OPnCxXPpQugAOJ7zclfdRVpVN07RAPJKjMpVeQ+87EEH5ZFWpuOortUrrGE8xac+OsDOzQzmNCkchcq6rhs3YuPb/U86a6RswimkOGl/J2wT4Dd9npnCtkNyhFKc1Ucr+z63qQ/Pc0binfmgQ9XpX6A0FdMHs0d2XQzgKMjtDVfEEfclVO9ieGUMziDDdNzSce9xeAKWFyXZGXX3kBvmYDJOcs0HRjggUQXhmrHmbff6hkCd8qn2yoTIHtBgSH8VCR0tbT8UEyJFmqrBRt5qdDk4ITiPomdxOcEmdG9ivPtcDgcvP5RMNwUSBbEMWPGn7SHv36Glzm0t4Z4PPZouLr8pnrBzR9xUrd/5soyul0XkkcRGeA9Nj5ChtSsTMZbK26sk3UQjwNCm3+arAouSw== abdullah.alotaishan@kcl.ac.uk"
  namespace    = "ucabbaa-comp0235-ns"
  network_name = "ds4eng"
  image_name   = "almalinux-9.4-20240805"
  username     = "ucabbaa@ucl.ac.uk"
}

resource "harvester_cloudinit_secret" "cloud_config" {
  name      = "${local.username}-cloudinit-${random_id.secret.hex}"
  namespace = local.namespace
  user_data = <<-EOF
  #cloud-config
  ssh_authorized_keys:
    - ${local.ssh_key}
  EOF
}

data "harvester_image" "img" {
  name      = "almalinux-9.4-20240805"
  namespace = "harvester-public"
}


# Management VM: CPU=2, Mem=4Gi, Disk=10Gi
resource "harvester_virtualmachine" "mgmt" {
  name                 = "${local.username}-mgmt-${random_id.secret.hex}"
  namespace            = local.namespace
  restart_after_update = true

  description = "Management Node"
  cpu    = 2
  memory = "4Gi"
  efi         = true
  secure_boot = false
  run_strategy    = "RerunOnFailure"
  hostname        = "${local.username}-mgmt-${random_id.secret.hex}"
  reserved_memory = "100Mi"
  machine_type    = "q35"

  network_interface {
    name           = "nic-1"
    wait_for_lease = true
    type           = "bridge"
    network_name   = local.network_name
  }

  disk {
    name       = "rootdisk"
    type       = "disk"
    size       = "10Gi"
    bus        = "virtio"
    boot_order = 1
    image      = data.harvester_image.img.id
    auto_delete = true
  }

  cloudinit {
    user_data_secret_name = harvester_cloudinit_secret.cloud_config.name
  }
}

# Workers: 3 VMs, CPU=4, Mem=32Gi, Disk=25Gi
resource "harvester_virtualmachine" "worker" {
  count               = 3
  name                = "${local.username}-worker-${count.index + 1}-${random_id.secret.hex}"
  namespace           = local.namespace
  restart_after_update = true

  description = "Worker Node"
  cpu    = 4
  memory = "32Gi"
  efi         = true
  secure_boot = false
  run_strategy    = "RerunOnFailure"
  hostname        = "${local.username}-worker-${count.index + 1}-${random_id.secret.hex}"
  reserved_memory = "100Mi"
  machine_type    = "q35"

  network_interface {
    name           = "nic-1"
    wait_for_lease = true
    type           = "bridge"
    network_name   = local.network_name
  }

  disk {
    name       = "rootdisk"
    type       = "disk"
    size       = "25Gi"
    bus        = "virtio"
    boot_order = 1
    image      = data.harvester_image.img.id
    auto_delete = true
  }

  cloudinit {
    user_data_secret_name = harvester_cloudinit_secret.cloud_config.name
  }
}

# Storage VM: CPU=4, Mem=8Gi, root=10Gi + extra 200Gi disk
resource "harvester_virtualmachine" "storage" {
  name                 = "${local.username}-storage-${random_id.secret.hex}"
  namespace            = local.namespace
  restart_after_update = true

  description = "Storage Node"
  cpu    = 4
  memory = "8Gi"
  efi         = true
  secure_boot = false
  run_strategy    = "RerunOnFailure"
  hostname        = "${local.username}-storage-${random_id.secret.hex}"
  reserved_memory = "100Mi"
  machine_type    = "q35"

  network_interface {
    name           = "nic-1"
    wait_for_lease = true
    type           = "bridge"
    network_name   = local.network_name
  }

  disk {
    name       = "rootdisk"
    type       = "disk"
    size       = "10Gi"
    bus        = "virtio"
    boot_order = 1
    image      = data.harvester_image.img.id
    auto_delete = true
  }

  disk {
    name       = "datadisk"
    type       = "disk"
    size       = "200Gi"
    bus        = "virtio"
    auto_delete = true
  }

  cloudinit {
    user_data_secret_name = harvester_cloudinit_secret.cloud_config.name
  }
}