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

