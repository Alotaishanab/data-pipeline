#!/usr/bin/env python3

import json
import subprocess
import argparse
import sys

def run(command):
    return subprocess.run(command, capture_output=True, text=True)

def get_terraform_ips():
    """
    Fetch mgmt, worker, and storage node IPs from Terraform output -json.
    We now look for 'mgmt_vm_ips', 'worker_vm_ips', and 'storage_vm_ips'.
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

    # If we fail to get mgmt_node or worker_nodes or storage_nodes, fail
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
    # Assign friendly hostnames
    mgmt_name = "host"
    storage_name = "storage"
    worker_names = [f"worker{i+1}" for i in range(len(worker_nodes))]

    host_vars = {
        mgmt_name: {"ansible_host": mgmt_node, "ip": [mgmt_node]},
        storage_name: {"ansible_host": storage_nodes[0], "ip": [storage_nodes[0]]}
    }

    for i, w_ip in enumerate(worker_nodes):
        host_vars[worker_names[i]] = {"ansible_host": w_ip, "ip": [w_ip]}

    inventory = {
        "_meta": {
            "hostvars": host_vars
        },
        "all": {
            "children": {
                "mgmtnode": {},
                "workers": {},
                "storage": {}
            }
        },
        "mgmtnode": {
            "hosts": {
                mgmt_name: None
            }
        },
        "storage": {
            "hosts": {
                storage_name: None
            }
        },
        "workers": {
            "hosts": {name: None for name in worker_names}
        }
    }

    jd = json.dumps(inventory, indent=4)
    return jd

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Generate a cluster inventory from Terraform outputs.",
        prog=__file__
    )

    mo = ap.add_mutually_exclusive_group()
    mo.add_argument("--list", action="store_true", help="Show JSON of all managed hosts")
    mo.add_argument("--host", action="store", help="Display vars related to the host")

    args = ap.parse_args()

    # If we query a specific host, just print empty vars
    if args.host:
        print(json.dumps({}))
        sys.exit(0)

    # Default to --list if no argument given
    if not args.list:
        args.list = True

    # Attempt to get IPs from Terraform
    mgmt_node, worker_nodes, storage_nodes = get_terraform_ips()

    # Generate inventory
    jd = generate_inventory(mgmt_node, worker_nodes, storage_nodes)

    # Save the generated inventory to a file
    inventory_file_path = "../ansible/inventories/inventory.json"  # Adjust path if needed
    with open(inventory_file_path, "w") as f:
        f.write(jd)

    print(f"Inventory saved to {inventory_file_path}")
    print(jd)
