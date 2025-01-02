#!/usr/bin/env python3

import json
import subprocess
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

def generate_inventory(mgmt_node, worker_nodes, storage_nodes):
    # Generate a simple inventory with just IPs
    inventory = {
        "all": {
            "children": {
                "mgmtnode": {},
                "workers": {},
                "storagegroup": {}
            }
        },
        "mgmtnode": {
            "hosts": {
                "host": {
                    "ansible_host": mgmt_node
                }
            }
        },
        "workers": {
            "hosts": {f"worker{i+1}": {"ansible_host": ip} for i, ip in enumerate(worker_nodes)}
        },
        "storagegroup": {
            "hosts": {
                "storage": {
                    "ansible_host": storage_nodes[0]
                }
            }
        }
    }
    
    return json.dumps(inventory, indent=4)

def main():
    outputs = get_terraform_outputs()
    mgmt_node, worker_nodes, storage_nodes = get_terraform_ips(outputs)
    
    inventory = generate_inventory(mgmt_node, worker_nodes, storage_nodes)
    
    inventory_file_path = "../ansible/inventories/inventory.json"
    with open(inventory_file_path, "w") as f:
        f.write(inventory)
    
    print(f"Inventory saved to {inventory_file_path}")
    print(inventory)

if __name__ == "__main__":
    main()
