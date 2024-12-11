#!/usr/bin/env python3

import json
import subprocess
import argparse

def run(command):
    return subprocess.run(command, capture_output=True, encoding='UTF-8')

def generate_inventory():
    # Fetch mgmt VM IPs (we know it's one VM, but output is an array)
    mgmt_node = input("Enter the Management Node IP: ")

    worker_nodes = input("Enter the Worker Node IPs (comma separated no space): ").split(',')
    storage_nodes = input("Enter the Storage Node IPs (comma separated no space): ").split(',')

    host_vars = {}
    host_vars[mgmt_node] = {"ip": [mgmt_node]}

    workers = []
    for worker in worker_nodes:
        workers.append(worker.strip())
        host_vars[worker.strip()] = {"ip": [worker.strip()]}

    for storage in storage_nodes:
        workers.append(storage.strip())
        host_vars[storage.strip()] = {"ip": [storage.strip()]}

    _meta = {"hostvars": host_vars}
    _all = {"children": ["mgmtnode", "workers"]}

    _workers = {"hosts": workers}
    _mgmtnode = {"hosts": [mgmt_node]}

    _jd = {
        "_meta": _meta,
        "all": _all,
        "workers": _workers,
        "mgmtnode": _mgmtnode
    }

    jd = json.dumps(_jd, indent=4)
    return jd

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Generate a cluster inventory from user input.",
        prog=__file__
    )

    mo = ap.add_mutually_exclusive_group()
    mo.add_argument("--list", action="store_true", help="Show JSON of all managed hosts")
    mo.add_argument("--host", action="store", help="Display vars related to the host")

    args = ap.parse_args()

    if args.host:
        # If we query a specific host, just print an empty vars dict
        print(json.dumps({}))
    elif args.list:
        jd = generate_inventory()
        # Save the generated inventory to a file
        with open("../../ansible/inventories/inventory.json", "w") as f:
            f.write(jd)
        print(f"Inventory saved to ../../ansible/inventories/inventory.json")
    else:
        # Default to --list behavior
        jd = generate_inventory()
        print(jd)
