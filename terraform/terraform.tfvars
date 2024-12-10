provider_endpoint = "https://rancher.condenser.arc.ucl.ac.uk/k8s/clusters/c-m-bv9x5ngh"
provider_token    = "kubeconfig-u-fhgdi4zayzt44cf:vpnbspq6drps267tt2cb2vm4s2l5mk6xxh79fjcvmx77g86mr98pj4"
provider_namespace= "ucabbaa-comp0235-ns"
username          = "ucabbaa@ucl.ac.uk"
ssh_key           = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDEG..." # Your full SSH key line
image_name        = "image-bp52g"                # Actual image resource name
image_namespace   = "harvester-public"           # Namespace where image resides
network_name      = "ucabbaa-comp0235-ns/ds4eng"

# VM Specs
mgmt_cpu          = 2
mgmt_memory       = "4Gi"
mgmt_disk_size    = "10Gi"

worker_count      = 3
worker_cpu        = 4
worker_memory     = "32Gi"
worker_disk_size  = "25Gi"

# Storage VM specs
storage_cpu       = 4
storage_memory    = "8Gi"
storage_root_disk_size = "10Gi"
storage_extra_disk_size = "200Gi"
