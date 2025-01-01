###############################################################################
# outputs.tf
###############################################################################

# Management VM IPs
output "mgmt_vm_ips" {
  value = [harvester_virtualmachine.mgmt.network_interface[0].ip_address]
}

# Worker VMs IPs
output "worker_vm_ips" {
  value = [for w in harvester_virtualmachine.worker : w.network_interface[0].ip_address]
}

# Storage VM IPs
output "storage_vm_ips" {
  value = [harvester_virtualmachine.storage.network_interface[0].ip_address]
}

# SSH Config (Optional)
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

# Management VM Tags
output "condenser_ingress_prometheus_hostname" {
  value = harvester_virtualmachine.mgmt.tags["condenser_ingress_prometheus_hostname"]
}

output "condenser_ingress_prometheus_port" {
  value = harvester_virtualmachine.mgmt.tags["condenser_ingress_prometheus_port"]
}

output "condenser_ingress_grafana_hostname" {
  value = harvester_virtualmachine.mgmt.tags["condenser_ingress_grafana_hostname"]
}

output "condenser_ingress_grafana_port" {
  value = harvester_virtualmachine.mgmt.tags["condenser_ingress_grafana_port"]
}

output "condenser_ingress_nodeexporter_hostname" {
  value = harvester_virtualmachine.mgmt.tags["condenser_ingress_nodeexporter_hostname"]
}

output "condenser_ingress_nodeexporter_port" {
  value = harvester_virtualmachine.mgmt.tags["condenser_ingress_nodeexporter_port"]
}

output "condenser_ingress_isAllowed" {
  value = harvester_virtualmachine.mgmt.tags["condenser_ingress_isAllowed"]
}

output "condenser_ingress_isEnabled" {
  value = harvester_virtualmachine.mgmt.tags["condenser_ingress_isEnabled"]
}

# Worker and Storage VM Tags
output "worker_storage_ingress_node_hostname" {
  value = [for w in harvester_virtualmachine.worker : w.tags["condenser_ingress_node_hostname"]]
}

output "worker_storage_ingress_node_port" {
  value = [for w in harvester_virtualmachine.worker : w.tags["condenser_ingress_node_port"]]
}

output "worker_storage_ingress_isAllowed" {
  value = [for w in harvester_virtualmachine.worker : w.tags["condenser_ingress_isAllowed"]]
}

output "worker_storage_ingress_isEnabled" {
  value = [for w in harvester_virtualmachine.worker : w.tags["condenser_ingress_isEnabled"]]
}

output "storage_ingress_node_hostname" {
  value = harvester_virtualmachine.storage.tags["condenser_ingress_node_hostname"]
}

output "storage_ingress_node_port" {
  value = harvester_virtualmachine.storage.tags["condenser_ingress_node_port"]
}

output "storage_ingress_isAllowed" {
  value = harvester_virtualmachine.storage.tags["condenser_ingress_isAllowed"]
}

output "storage_ingress_isEnabled" {
  value = harvester_virtualmachine.storage.tags["condenser_ingress_isEnabled"]
}

output "admin_email" {
  description = "The admin email address for Certbot notifications."
  value       = var.username
}