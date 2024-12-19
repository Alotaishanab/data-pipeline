#!/usr/bin/env python3
from flask import Flask, request
import subprocess
import json
import os
import logging
import sys

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    filename='/opt/data_pipeline/alert_receiver.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Absolute path to your Ansible inventory.json
INVENTORY_PATH = "/home/almalinux/data-pipeline/ansible/inventories/inventory.json"

def load_inventory_mapping():
    try:
        with open(INVENTORY_PATH, 'r') as f:
            inventory = json.load(f)
        logging.info("Loaded inventory.json successfully.")
    except Exception as e:
        logging.error(f"Error loading inventory file: {e}")
        return {}
    
    workers = inventory.get('workers', {}).get('hosts', {})
    mapping = {}
    for worker, details in workers.items():
        ip = details.get('ansible_host')
        if ip:
            mapping[ip] = worker
            logging.debug(f"Mapped IP {ip} to worker {worker}.")
    return mapping

# Load the mapping at startup
INSTANCE_TO_WORKER = load_inventory_mapping()
logging.info(f"Instance to Worker Mapping: {INSTANCE_TO_WORKER}")

# Absolute paths to your scripts
CLEANUP_PLAYBOOK_PATH = "/home/almalinux/data-pipeline/ansible/playbooks/cleanup_disk_space.yml"
UPDATE_WORKERS_SCRIPT = "/opt/data_pipeline/update_disabled_workers.py"

@app.route('/alertmanager-webhook', methods=['POST'])
def alertmanager_webhook():
    data = request.json
    if not data:
        logging.warning("No JSON payload received.")
        return '', 200

    alerts = data.get('alerts', [])
    for alert in alerts:
        alertname = alert.get('labels', {}).get('alertname')
        status = alert.get('status')  # 'firing' or 'resolved'
        instance = alert.get('labels', {}).get('instance', 'unknown').split(':')[0]  # Extract IP

        logging.info(f"Received alert: {alertname} for instance: {instance} with status: {status}")

        worker_name = INSTANCE_TO_WORKER.get(instance)
        if not worker_name:
            logging.warning(f"No mapping found for instance: {instance}")
            continue

        if alertname == 'HighDiskUsage' and status == 'firing':
            logging.info(f"HighDiskUsage alert firing for worker: {worker_name}")
            # Run the cleanup disk space playbook
            process = subprocess.run([
                "ansible-playbook",
                "-i", INVENTORY_PATH,
                "--limit", worker_name, 
                CLEANUP_PLAYBOOK_PATH
            ], capture_output=True, text=True, check=False)

            logging.info(f"Executed cleanup_disk_space.yml playbook.")
            logging.info(f"Cleanup stdout: {process.stdout}")
            logging.info(f"Cleanup stderr: {process.stderr}")
            logging.info(f"Cleanup returncode: {process.returncode}")

        if alertname == 'HighCPULoad':
            if status == 'firing':
                logging.info(f"HighCPULoad alert firing for worker: {worker_name} - Disabling worker")
                # Disable worker
                process = subprocess.run([
                    "python3",
                    UPDATE_WORKERS_SCRIPT,
                    worker_name,
                    "disable"
                ], capture_output=True, text=True, check=False)
                
                logging.info(f"Executed update_disabled_workers.py to disable {worker_name}.")
                logging.info(f"Disable stdout: {process.stdout}")
                logging.info(f"Disable stderr: {process.stderr}")
                logging.info(f"Disable returncode: {process.returncode}")

            elif status == 'resolved':
                logging.info(f"HighCPULoad alert resolved for worker: {worker_name} - Enabling worker")
                # Re-enable worker
                process = subprocess.run([
                    "python3",
                    UPDATE_WORKERS_SCRIPT,
                    worker_name,
                    "enable"
                ], capture_output=True, text=True, check=False)

                logging.info(f"Executed update_disabled_workers.py to enable {worker_name}.")
                logging.info(f"Enable stdout: {process.stdout}")
                logging.info(f"Enable stderr: {process.stderr}")
                logging.info(f"Enable returncode: {process.returncode}")

    return '', 200

if __name__ == '__main__':
    # Run on port 8080, accessible to Alertmanager
    app.run(host='0.0.0.0', port=8080)
