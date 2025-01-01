#!/usr/bin/env python3

import json
import subprocess
import argparse
import sys

def run(command):
    return subprocess.run(command, capture_output=True, text=True)

def get_terraform_outputs():
    """
    Fetch all Terraform outputs in JSON format.
    """
    tf = run(["terraform", "output", "-json"])
    if tf.returncode != 0:
        print("Error: Could not run 'terraform output -json'. Please ensure Terraform is initialized.")
        sys.exit(1)
    
    try:
        outputs = json.loads(tf.stdout)
    except json.JSONDecodeError:
        print("Error: Could not parse Terraform outputs as JSON.")
        sys.exit(1)
    
    return outputs

def get_terraform_ips(outputs):
    """
    Extract mgmt, worker, and storage node IPs from Terraform outputs.
    """
    mgmt_node = None
    worker_nodes = []
    storage_nodes = []
    
    if "mgmt_vm_ips" in outputs and outputs["mgmt_vm_ips"]["value"]:
        mgmt_list = outputs["mgmt_vm_ips"]["value"]
        if isinstance(mgmt_list, list) and len(mgmt_list) > 0:
            mgmt_node = mgmt_list[0]
    
    if "worker_vm_ips" in outputs and outputs["worker_vm_ips"]["value"]:
        w_list = outputs["worker_vm_ips"]["value"]
        if isinstance(w_list, list):
            worker_nodes = w_list
    
    if "storage_vm_ips" in outputs and outputs["storage_vm_ips"]["value"]:
        s_list = outputs["storage_vm_ips"]["value"]
        if isinstance(s_list, list):
            storage_nodes = s_list
    
    # Fail if we can't find required IPs
    if not mgmt_node:
        print("Error: No mgmt_vm_ips found in Terraform outputs.")
        sys.exit(1)
    if not worker_nodes:
        print("Error: No worker_vm_ips found in Terraform outputs.")
        sys.exit(1)
    if not storage_nodes:
        print("Error: No storage_vm_ips found in Terraform outputs.")
        sys.exit(1)
    
    return mgmt_node, worker_nodes, storage_nodes

def generate_inventory(mgmt_node, worker_nodes, storage_nodes, outputs, base_domain):
    # Friendly hostnames
    mgmt_name = "host"
    storage_name = "storage"
    storage_group = "storagegroup"
    worker_names = [f"worker{i+1}" for i in range(len(worker_nodes))]
    
    # Extract management VM tags
    mgmt_tags = {
        "condenser_ingress_prometheus_hostname": outputs.get("condenser_ingress_prometheus_hostname", {}).get("value", "") + f".{base_domain}",
        "condenser_ingress_prometheus_port": outputs.get("condenser_ingress_prometheus_port", {}).get("value", ""),
        "condenser_ingress_grafana_hostname": outputs.get("condenser_ingress_grafana_hostname", {}).get("value", "") + f".{base_domain}",
        "condenser_ingress_grafana_port": outputs.get("condenser_ingress_grafana_port", {}).get("value", ""),
        "condenser_ingress_nodeexporter_hostname": outputs.get("condenser_ingress_nodeexporter_hostname", {}).get("value", "") + f".{base_domain}",
        "condenser_ingress_nodeexporter_port": outputs.get("condenser_ingress_nodeexporter_port", {}).get("value", ""),
        "condenser_ingress_isAllowed": outputs.get("condenser_ingress_isAllowed", {}).get("value", ""),
        "condenser_ingress_isEnabled": outputs.get("condenser_ingress_isEnabled", {}).get("value", ""),
        "admin_email": outputs.get("admin_email", {}).get("value", "")
    }
    
    # Extract worker VM tags (as lists)
    worker_tags = {
        "condenser_ingress_node_hostname": outputs.get("worker_storage_ingress_node_hostname", {}).get("value", []),
        "condenser_ingress_node_port": outputs.get("worker_storage_ingress_node_port", {}).get("value", []),
        "condenser_ingress_isAllowed": outputs.get("worker_storage_ingress_isAllowed", {}).get("value", []),
        "condenser_ingress_isEnabled": outputs.get("worker_storage_ingress_isEnabled", {}).get("value", [])
    }
    
    # Extract storage VM tags
    storage_tags = {
        "condenser_ingress_node_hostname": outputs.get("storage_ingress_node_hostname", {}).get("value", "") + f".{base_domain}",
        "condenser_ingress_node_port": outputs.get("storage_ingress_node_port", {}).get("value", ""),
        "condenser_ingress_isAllowed": outputs.get("storage_ingress_isAllowed", {}).get("value", ""),
        "condenser_ingress_isEnabled": outputs.get("storage_ingress_isEnabled", {}).get("value", "")
    }
    
    # mgmtnode group with hosts list
    mgmtnode_group = {
        "hosts": [mgmt_name]
    }
    
    # storagegroup group with hosts list
    storage_group_dict = {
        "hosts": [storage_name]
    }
    
    # workers group with hosts list
    workers_group = {
        "hosts": worker_names
    }
    
    # hostvars
    hostvars = {
        mgmt_name: {
            "ansible_host": mgmt_node,
            **mgmt_tags
        },
        storage_name: {
            "ansible_host": storage_nodes[0],
            **storage_tags
        }
    }
    
    for i, w_ip in enumerate(worker_nodes):
        host_name = worker_names[i]
        hostvars[host_name] = {
            "ansible_host": w_ip,
            "condenser_ingress_node_hostname": worker_tags["condenser_ingress_node_hostname"][i] + f".{base_domain}" if i < len(worker_tags["condenser_ingress_node_hostname"]) else "",
            "condenser_ingress_node_port": worker_tags["condenser_ingress_node_port"][i] if i < len(worker_tags["condenser_ingress_node_port"]) else "",
            "condenser_ingress_isAllowed": worker_tags["condenser_ingress_isAllowed"][i] if i < len(worker_tags["condenser_ingress_isAllowed"]) else "",
            "condenser_ingress_isEnabled": worker_tags["condenser_ingress_isEnabled"][i] if i < len(worker_tags["condenser_ingress_isEnabled"]) else ""
        }
    
    # all group with children as a list
    inventory = {
        "all": {
            "children": ["mgmtnode", "workers", "storagegroup"]
        },
        "mgmtnode": mgmtnode_group,
        "storagegroup": storage_group_dict,
        "workers": workers_group,
        "_meta": {
            "hostvars": hostvars
        }
    }
    
    jd = json.dumps(inventory, indent=4)
    return jd

def main():
    ap = argparse.ArgumentParser(
        description="Generate a cluster inventory from Terraform outputs.",
        prog=__file__
    )
    
    mo = ap.add_mutually_exclusive_group()
    mo.add_argument("--list", action="store_true", help="Show JSON of all managed hosts")
    mo.add_argument("--host", action="store", help="Display vars related to the host")
    
    args = ap.parse_args()
    
    if args.host:
        # If we query a specific host, print empty vars
        print(json.dumps({}))
        sys.exit(0)
    
    if not args.list:
        args.list = True
    
    outputs = get_terraform_outputs()
    mgmt_node, worker_nodes, storage_nodes = get_terraform_ips(outputs)
    
    # Define your base domain
    base_domain = "harvesterhci.io"
    
    jd = generate_inventory(mgmt_node, worker_nodes, storage_nodes, outputs, base_domain)
    
    inventory_file_path = "../ansible/inventories/inventory.json"
    with open(inventory_file_path, "w") as f:
        f.write(jd)
    
    print(f"Inventory saved to {inventory_file_path}")
    print(jd)

if __name__ == "__main__":
    main()
