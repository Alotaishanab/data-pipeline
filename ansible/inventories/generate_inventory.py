#!/usr/bin/env python3

import json
import subprocess
import argparse

def run(command):
    return subprocess.run(command, capture_output=True, encoding='UTF-8')

def generate_inventory():
    # Fetch mgmt VM IPs (we know it's one VM, but output is an array)
    mgmt_command = "terraform output --json mgmt_vm_ips".split()
    mgmt_data = json.loads(run(mgmt_command).stdout)
    # mgmt_data should be an array with one IP
    mgmt_node = mgmt_data[0]

    host_vars = {}
    host_vars[mgmt_node] = {"ip": [mgmt_node]}

    # Fetch worker VM IPs
    worker_command = "terraform output --json vm_ips".split()
    ip_data = json.loads(run(worker_command).stdout)

    workers = []
    for a in ip_data:
        workers.append(a)
        host_vars[a] = {"ip": [a]}

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
        description="Generate a cluster inventory from Terraform.",
        prog=__file__
    )

    mo = ap.add_mutually_exclusive_group()
    mo.add_argument("--list", action="store", nargs="*", default="dummy", help="Show JSON of all managed hosts")
    mo.add_argument("--host", action="store", help="Display vars related to the host")

    args = ap.parse_args()

    if args.host:
        # If we query a specific host, just print an empty vars dict
        print(json.dumps({}))
    elif len(args.list) >= 0:
        jd = generate_inventory()
        print(jd)
    else:
        raise ValueError("Expecting either --host $HOSTNAME or --list")
