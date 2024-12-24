#!/usr/bin/env python3
from flask import Flask, request
import subprocess
import json
import logging

app = Flask(__name__)
logging.basicConfig(
    filename='/opt/data_pipeline/alert_receiver.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

INVENTORY_PATH = "/home/almalinux/data-pipeline/ansible/inventories/inventory.json"
CLEANUP_PLAYBOOK_PATH = "/home/almalinux/data-pipeline/ansible/playbooks/cleanup_disk_space.yml"
UPDATE_WORKERS_SCRIPT = "/opt/data_pipeline/update_disabled_workers.py"

def load_inventory_mapping():
    try:
        with open(INVENTORY_PATH, 'r') as f:
            inventory = json.load(f)
        workers = inventory.get('workers', {}).get('hosts', {})
        mapping = {}
        for worker, details in workers.items():
            ip = details.get('ansible_host')
            if ip:
                mapping[ip] = worker
        return mapping
    except Exception as e:
        logging.error(f"Error reading inventory: {e}")
        return {}

INSTANCE_TO_WORKER = load_inventory_mapping()

@app.route('/alertmanager-webhook', methods=['POST'])
def alertmanager_webhook():
    data = request.json or {}
    alerts = data.get('alerts', [])
    for alert in alerts:
        alertname = alert.get('labels', {}).get('alertname')
        status = alert.get('status')
        instance = alert.get('labels', {}).get('instance', '').split(':')[0]
        worker_name = INSTANCE_TO_WORKER.get(instance)
        if not worker_name:
            continue

        # HighDiskUsage cleanup (unchanged)
        if alertname == 'HighDiskUsage' and status == 'firing':
            subprocess.run(["ansible-playbook", CLEANUP_PLAYBOOK_PATH], check=False)

        # HighCPULoad logic
        if alertname == 'HighCPULoad':
            if status == 'firing':
                # Disable worker in Redis
                subprocess.run(["python3", UPDATE_WORKERS_SCRIPT, worker_name, "disable"], check=False)

                # Stop Celery service with Ansible
                stop_cmd = [
                    "ansible", worker_name,
                    "-m", "service",
                    "-a", "name=celery state=stopped",
                    "-b"  # become: yes
                ]
                stop_result = subprocess.run(stop_cmd, capture_output=True, text=True)
                if stop_result.returncode != 0:
                    logging.error(f"Failed to stop Celery on {worker_name}. Return code: {stop_result.returncode}")
                    logging.error(f"Ansible stderr: {stop_result.stderr}")
                else:
                    logging.info(f"Celery stopped on {worker_name} successfully.")

            elif status == 'resolved':
                # Re-enable worker in Redis
                subprocess.run(["python3", UPDATE_WORKERS_SCRIPT, worker_name, "enable"], check=False)

                # Start Celery service with Ansible
                start_cmd = [
                    "ansible", worker_name,
                    "-m", "service",
                    "-a", "name=celery state=started",
                    "-b"
                ]
                start_result = subprocess.run(start_cmd, capture_output=True, text=True)
                if start_result.returncode != 0:
                    logging.error(f"Failed to start Celery on {worker_name}. Return code: {start_result.returncode}")
                    logging.error(f"Ansible stderr: {start_result.stderr}")
                    # Optionally revert if start fails
                else:
                    logging.info(f"Celery started on {worker_name} successfully.")

    return '', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
