output "mgmt_vm_ips" {
  value = [harvester_virtualmachine.mgmt.network_interface[0].ip_address]
}

output "worker_vm_ips" {
  value = [for w in harvester_virtualmachine.worker : w.network_interface[0].ip_address]
}

output "storage_vm_ips" {
  value = [harvester_virtualmachine.storage.network_interface[0].ip_address]
}
