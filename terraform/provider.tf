terraform {
  required_version = ">= 1.0.0"
  required_providers {
    harvester = {
      source  = "harvester/harvester"
      version = ">= 0.2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.1.0"
    }
  }
}

provider "harvester" {
  kubeconfig_raw = <<-EOF
apiVersion: v1
kind: Config
clusters:
- name: "sl-p01"
  cluster:
    server: "https://rancher.condenser.arc.ucl.ac.uk/k8s/clusters/c-m-bv9x5ngh"
    certificate-authority-data: "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUJ2VENDQ\
VdPZ0F3SUJBZ0lCQURBS0JnZ3Foa2pPUFFRREFqQkdNUnd3R2dZRFZRUUtFeE5rZVc1aGJXbGoKY\
kdsemRHVnVaWEl0YjNKbk1TWXdKQVlEVlFRRERCMWtlVzVoYldsamJHbHpkR1Z1WlhJdFkyRkFNV\
GN3T1RBMApOak01TVRBZUZ3MHlOREF5TWpjeE5UQTJNekZhRncwek5EQXlNalF4TlRBMk16RmFNR\
Vl4SERBYUJnTlZCQW9UCkUyUjVibUZ0YVdOc2FYTjBaVzVsY2kxdmNtY3hKakFrQmdOVkJBTU1IV\
1I1Ym1GdGFXTnNhWE4wWlc1bGNpMWoKWVVBeE56QTVNRFEyTXpreE1Ga3dFd1lIS29aSXpqMENBU\
VlJS29aSXpqMERBUWNEUWdBRXVrYjRsVHdScmlwOApBT2RTcjhJWXN1NXFGZTNtb0lWWDFTQ3lVe\
GE1U0FSMSsvQTNlaVY5WWJIcXpTUlZxU0NiRFVEZncyWnVNcTFvCnY2VVBOUmlqdmFOQ01FQXdEZ\
1lEVlIwUEFRSC9CQVFEQWdLa01BOEdBMVVkRXdFQi93UUZNQU1CQWY4d0hRWUQKVlIwT0JCWUVGR\
E1NclVsV3pGNlJmQ2N4WVR3N0R1V0JJSFlNTUFvR0NDcUdTTTQ5QkFNQ0EwZ0FNRVVDSUMwVApGZ\
0JyS1F6WHFYdEtXOVV6dUZEVW9meFVKcVdUTW1NWVdmRFVJa1JYQWlFQXpxSHY3NjBneWI0SzRpb\
TZweTNlCmZVdU1TTFVXVjd0TFhXTlhyU2pPN0NrPQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0t"

users:
- name: "sl-p01"
  user:
    token: "kubeconfig-u-fhgdi4zayztbpvr:dwrdmsvv68wbnq7vp7sb25bgl9qgmk466dghxvwb7ns756g8ggcn9b"

contexts:
- name: "sl-p01"
  context:
    user: "sl-p01"
    cluster: "sl-p01"

current-context: "sl-p01"
EOF
}
