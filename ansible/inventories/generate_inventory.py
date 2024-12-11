#!/usr/bin/env python3

import json
import subprocess
import argparse

def run(command):
    return subprocess.run(command, capture_output=True, encoding='UTF-8')

def generate_inventory(mgmt_ip, worker_ips, storage_ips):
    host_vars = {}
    
    # Add management node IP
    host_vars[mgmt_ip] = {"ip": [mgmt_ip]}

    workers = []
    for ip in worker_ips:
        workers.append(ip)
        host_vars[ip] = {"ip": [ip]}

    # Add storage node IPs
    for ip in storage_ips:
        workers.append(ip)
        host_vars[ip] = {"ip": [ip]}

    _meta = {"hostvars": host_vars}
    _all = {"children": ["mgmtnode", "workers"]}

    _workers = {"hosts": workers}
    _mgmtnode = {"hosts": [mgmt_ip]}

    _jd = {
        "_meta": _meta,
        "all": _all,
        "workers": _workers,
        "mgmtnode": _mgmtnode
    }

    jd = json.dumps(_jd, indent=4)
    return jd

def get_ips_from_input():
    mgmt_ip = input("Enter the Management Node IP: ")
    worker_ips = input("Enter the Worker Node IPs (comma separated): ").split(',')
    storage_ips = input("Enter the Storage Node IPs (comma separated): ").split(',')

    return mgmt_ip, worker_ips, storage_ips

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Generate a cluster inventory with dynamic IPs.",
        prog=__file__
    )

    mo = ap.add_mutually_exclusive_group()
    mo.add_argument("--list", action="store_true", help="Show JSON of all managed hosts")
    mo.add_argument("--host", action="store", help="Display vars related to the host")

    args = ap.parse_args()

    if args.host:
        print(json.dumps({}))
    elif args.list:
        mgmt_ip, worker_ips, storage_ips = get_ips_from_input()
        jd = generate_inventory(mgmt_ip, worker_ips, storage_ips)
        print(jd)
    else:
        mgmt_ip, worker_ips, storage_ips = get_ips_from_input()
        jd = generate_inventory(mgmt_ip, worker_ips, storage_ips)
        print(jd)
