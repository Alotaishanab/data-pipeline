######################################
# main.tf - Combining Old & Ansible Key
######################################

locals {
  # Transform 'ucabbaa@ucl.ac.uk' into 'ucabbaa-ucl-ac-uk'
  sanitized_username = replace(replace(var.username, "@", "-"), ".", "-")
}

resource "random_id" "secret" {
  byte_length = 4
}

###############################################
# Single Cloud-Init for All VMs (Host, Worker, Storage)
# - Contains your key & marker's key
# - Contains a runcmd in the Host VM
#   that generates an internal Ansible key
###############################################

resource "harvester_cloudinit_secret" "cloud_config" {
  name      = "${local.sanitized_username}-cloudinit-${random_id.secret.hex}"
  namespace = var.provider_namespace

  # The same user_data for ALL VMs, just like your old approach,
  # plus extra runcmd lines that ONLY matter on the Host VM.
  # (They run on Workers too, but won't break anything.)
  user_data = <<-EOF
  #cloud-config

  # 1. Your & Marker’s Keys for All VMs
  ssh_authorized_keys:
    - ${var.ssh_key}
    - ${var.ssh_key_marker}

  # 2. Commands for first boot on any VM
  runcmd:
    # 2.1. Basic setup (same as old approach)
    - yum install -y epel-release
    - yum install -y ansible git

    # 2.2. Clone the Git repository (same as old approach)
    - git clone https://github.com/Alotaishanab/data-pipeline.git /home/almalinux/data-pipeline

    # 2.3. Additional step (mainly relevant on Host):
    #     Generate an Ansible key inside the Host, so it can do internal ansible tasks.
    #     This won't break Workers/Storage if run there, but you can ignore it on them.
    - ssh-keygen -t ed25519 -q -N "" -f /home/almalinux/.ssh/ansible_ed25519
    - cat /home/almalinux/.ssh/ansible_ed25519.pub >> /home/almalinux/.ssh/authorized_keys
    - chown almalinux:almalinux /home/almalinux/.ssh/ansible_ed25519*

    # Optionally, you can place an ansible.cfg or do more host-only steps here.
  EOF
}

#########################################
# Data Source for the Harvester Image
#########################################

data "harvester_image" "img" {
  name      = var.image_name
  namespace = var.image_namespace
}

#########################################
# 1. Management VM (Host)
#########################################

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

#########################################
# 2. Worker VMs
#########################################

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
    # Same user_data as mgmt, so your & marker keys are injected
    # The runcmd includes 'ssh-keygen', but it's safe & harmless here.
    user_data_secret_name = harvester_cloudinit_secret.cloud_config.name
  }
}

#########################################
# 3. Storage VM
#########################################

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
