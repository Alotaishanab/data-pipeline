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
            if ip: mapping[ip] = worker
        return mapping
    except Exception as e:
        logging.error(f"Error: {e}")
        return {}

INSTANCE_TO_WORKER = load_inventory_mapping()

@app.route('/alertmanager-webhook', methods=['POST'])
def alertmanager_webhook():
    data = request.json or {}
    alerts = data.get('alerts', [])
    for alert in alerts:
        alertname = alert.get('labels', {}).get('alertname')
        status = alert.get('status')
        instance = alert.get('labels', {}).get('instance','').split(':')[0]
        worker_name = INSTANCE_TO_WORKER.get(instance)
        if not worker_name: continue

        if alertname == 'HighDiskUsage' and status == 'firing':
            subprocess.run([
                "ansible-playbook", "-i",
                "/home/almalinux/ansible/inventories/inventory.json",
                CLEANUP_PLAYBOOK_PATH
            ], check=False)

        if alertname == 'HighCPULoad':
            # Derive queue from worker name if naming is consistent
            worker_queue = f"{worker_name}_queue"
            if status == 'firing':
                subprocess.run(["python3", UPDATE_WORKERS_SCRIPT, worker_name, "disable"], check=False)
                subprocess.run([
                    "celery", "-A", "celery_worker", "control",
                    "cancel_consumer", worker_queue,
                    "-d", f"celery@{worker_name}"
                ], check=False)
            elif status == 'resolved':
                subprocess.run(["python3", UPDATE_WORKERS_SCRIPT, worker_name, "enable"], check=False)
                subprocess.run([
                    "celery", "-A", "celery_worker", "control",
                    "add_consumer", worker_queue,
                    "-d", f"celery@{worker_name}"
                ], check=False)
    return '', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
