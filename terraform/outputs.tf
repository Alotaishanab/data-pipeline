output "mgmt_vm_ips" {
  value = [harvester_virtualmachine.mgmt.network_interface[0].ip_address]
}

output "worker_vm_ips" {
  value = [for w in harvester_virtualmachine.worker : w.network_interface[0].ip_address]
}

output "storage_vm_ips" {
  value = [harvester_virtualmachine.storage.network_interface[0].ip_address]
}

output "ssh_config" {
  value = <<-EOT
    # Host Machine
    Host host
        HostName ${harvester_virtualmachine.mgmt.network_interface[0].ip_address}
        User almalinux
        IdentityFile ~/.ssh/id_rsa                    # Correct SSH private key
        ProxyJump condenser-proxy

    # Worker Machines
    Host worker1
        HostName ${harvester_virtualmachine.worker[0].network_interface[0].ip_address}
        User almalinux
        IdentityFile ~/.ssh/id_rsa                    # Correct SSH private key
        ProxyJump condenser-proxy

    Host worker2
        HostName ${harvester_virtualmachine.worker[1].network_interface[0].ip_address}
        User almalinux
        IdentityFile ~/.ssh/id_rsa                    # Correct SSH private key
        ProxyJump condenser-proxy

    Host worker3
        HostName ${harvester_virtualmachine.worker[2].network_interface[0].ip_address}
        User almalinux
        IdentityFile ~/.ssh/id_rsa                    # Correct SSH private key
        ProxyJump condenser-proxy

    # Storage Machine
    Host storage
        HostName ${harvester_virtualmachine.storage.network_interface[0].ip_address}
        User almalinux
        IdentityFile ~/.ssh/id_rsa                    # Correct SSH private key
        ProxyJump condenser-proxy
  EOT
}

