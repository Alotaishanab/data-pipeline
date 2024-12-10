output "mgmt_vm_ips" {
  # Adjust based on the actual attribute from the Harvester provider
  value = [harvester_virtualmachine.mgmt.network_interface[0].ip_address]
}

output "vm_ips" {
  value = [for w in harvester_virtualmachine.worker : w.network_interface[0].ip_address]
}
