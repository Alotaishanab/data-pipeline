###############################################################################
# main.tf
###############################################################################

##########################################
# 0. Locals & Random ID
##########################################

# Example: transform 'ucabbaa@ucl.ac.uk' into 'ucabbaa-ucl-ac-uk'
locals {
  sanitized_username = replace(replace(var.username, "@", "-"), ".", "-")
}

resource "random_id" "secret" {
  byte_length = 4
}

##########################################
# 1. Generate Ephemeral Key for Ansible
##########################################

# This creates a brand-new RSA keypair each time.
# - tls_private_key.ansible.private_key_openssh -> private key
# - tls_private_key.ansible.public_key_openssh  -> public key
##########################################
resource "tls_private_key" "ansible" {
  algorithm = "RSA"
}

##########################################
# 2. Cloud-Init for the Host VM
##########################################
# - Contains your & Marker’s public keys,
# - Also places the ephemeral Ansible PRIVATE key onto the Host
# - Appends the ephemeral Ansible PUBLIC key to Host authorized_keys
##########################################
resource "harvester_cloudinit_secret" "cloudinit_host" {
  name      = "${local.sanitized_username}-cloudinit-host-${random_id.secret.hex}"
  namespace = var.provider_namespace

  user_data = <<-EOF
    #cloud-config

    # 1. Your & Marker’s Keys (allow you both to SSH in)
    ssh_authorized_keys:
      - ${var.ssh_key}
      - ${var.ssh_key_marker}
      - ${tls_private_key.ansible.private_key_openssh}

    # 2. First-boot commands
    runcmd:
      # 2.1 Basic packages & repo clone
      - yum install -y epel-release
      - yum install -y ansible git
      - git clone https://github.com/Alotaishanab/data-pipeline.git /home/almalinux/data-pipeline

      # 2.2 Write the ephemeral Ansible PRIVATE key from Terraform to disk
      - |
        echo "${tls_private_key.ansible.private_key_openssh}" > /home/almalinux/.ssh/ansible_rsa
        chmod 600 /home/almalinux/.ssh/ansible_rsa
        chown almalinux:almalinux /home/almalinux/.ssh/ansible_rsa

      # 2.3 Also append the ephemeral public key to Host's authorized_keys
      - |
        echo "${tls_private_key.ansible.public_key_openssh}" >> /home/almalinux/.ssh/authorized_keys
        chown almalinux:almalinux /home/almalinux/.ssh/authorized_keys

  EOF
}

##########################################
# 3. Cloud-Init for Workers & Storage
##########################################
# - Also includes your & marker’s public keys
# - Includes the ephemeral Ansible PUBLIC key (so Host can SSH in)
# - Doesn't store the private key
##########################################
resource "harvester_cloudinit_secret" "cloudinit_workerstorage" {
  name      = "${local.sanitized_username}-cloudinit-wkrstr-${random_id.secret.hex}"
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
      # No new keygen here, since the Host orchestrates everything

  EOF
}

#########################################
# 4. Data Source for Harvester Image
#########################################
data "harvester_image" "img" {
  name      = var.image_name
  namespace = var.image_namespace
}

#########################################
# 5. Management VM (Host)
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
    # Use the "cloudinit_host" secret, which includes the Host's private key
    user_data_secret_name = harvester_cloudinit_secret.cloudinit_host.name
  }
}

#########################################
# 6. Worker VMs
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
    # Use the "cloudinit_workerstorage" secret, which includes only public keys
    user_data_secret_name = harvester_cloudinit_secret.cloudinit_workerstorage.name
  }
}

#########################################
# 7. Storage VM
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
    # Same as worker, no private key
    user_data_secret_name = harvester_cloudinit_secret.cloudinit_workerstorage.name
  }
}



