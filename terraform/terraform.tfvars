###############################################################################
# terraform.tfvars
###############################################################################

provider_endpoint  = "https://rancher.condenser.arc.ucl.ac.uk/k8s/clusters/c-m-bv9x5ngh"
provider_token     = "kubeconfig-u-fhgdi4zayztbpvr:dwrdmsvv68wbnq7vp7sb25bgl9qgmk466dghxvwb7ns756g8ggcn9b"
provider_namespace = "ucabbaa-comp0235-ns"
username           = "ucabbaa@ucl.ac.uk"   

keyfile       = "../keys/id_rsa.pub"
marker_keyfile = "../keys/lecturer_key.pub"



image_name      = "image-bp52g"
image_namespace = "harvester-public"
network_name    = "ucabbaa-comp0235-ns/ds4eng"

# VM Specs
mgmt_cpu       = 2
mgmt_memory    = "4Gi"
mgmt_disk_size = "10Gi"

worker_count     = 3
worker_cpu       = 4
worker_memory    = "32Gi"
worker_disk_size = "25Gi"

# Storage VM specs
storage_cpu             = 4
storage_memory          = "8Gi"
storage_root_disk_size  = "10Gi"
storage_extra_disk_size = "200Gi"

# Instance Tags for Management VM
mgmt_vm_tags = {
  "condenser_ingress_prometheus_hostname"   = "-prom"
  "condenser_ingress_prometheus_port"       = "9090"
  "condenser_ingress_grafana_hostname"      = "-graf"
  "condenser_ingress_grafana_port"          = "3000"
  "condenser_ingress_nodeexporter_hostname" = "-node"
  "condenser_ingress_nodeexporter_port"     = "9100"
  "condenser_ingress_webserver_hostname"    = "-web"
  "condenser_ingress_isAllowed"             = "true"
  "condenser_ingress_isEnabled"             = "true"
}

# Instance Tags for Worker and Storage VMs
worker_storage_vm_tags = {
  "condenser_ingress_node_hostname" = "-node"
  "condenser_ingress_node_port"     = "9100"
  "condenser_ingress_isAllowed"     = "true"
  "condenser_ingress_isEnabled"     = "true"
}
