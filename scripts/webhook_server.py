#!/usr/bin/env python3
from flask import Flask, request
import subprocess
import json
import logging
import fcntl
import os
import time

app = Flask(__name__)
logging.basicConfig(
    filename='/opt/data_pipeline/alert_receiver.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

INVENTORY_PATH = "/home/almalinux/data-pipeline/ansible/inventories/inventory.json"
CLEANUP_PLAYBOOK_PATH = "/home/almalinux/data-pipeline/ansible/playbooks/cleanup_disk_space.yml"
UPDATE_WORKERS_SCRIPT = "/opt/data_pipeline/update_disabled_workers.py"
LOCK_FILE_PATH = "/tmp/alert_receiver.lock"
LOCK_TIMEOUT = 10  # seconds

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
        logging.info("Successfully loaded inventory mapping.")
        return mapping
    except Exception as e:
        logging.error(f"Error reading inventory: {e}")
        return {}

INSTANCE_TO_WORKER = load_inventory_mapping()

def acquire_lock(lock_file, timeout=LOCK_TIMEOUT):
    start_time = time.time()
    while True:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            logging.debug("Lock acquired.")
            return True
        except IOError:
            if (time.time() - start_time) >= timeout:
                logging.error("Timeout while waiting to acquire lock.")
                return False
            logging.debug("Lock is held by another process. Waiting...")
            time.sleep(0.5)

@app.route('/alertmanager-webhook', methods=['POST'])
def alertmanager_webhook():
    data = request.json or {}
    alerts = data.get('alerts', [])
    
    if not alerts:
        logging.info("No alerts received.")
        return '', 200
    
    with open(LOCK_FILE_PATH, 'w') as lock_file:
        if not acquire_lock(lock_file):
            logging.error("Could not acquire lock. Skipping alert processing.")
            return '', 503  # Service Unavailable
        
        try:
            for alert in alerts:
                alertname = alert.get('labels', {}).get('alertname')
                status = alert.get('status')
                instance = alert.get('labels', {}).get('instance', '').split(':')[0]
                worker_name = INSTANCE_TO_WORKER.get(instance)
                
                if not worker_name:
                    logging.warning(f"No worker mapping found for instance: {instance}")
                    continue

                logging.info(f"Processing alert: {alertname} for worker: {worker_name} with status: {status}")

                # HighDiskUsage cleanup
                if alertname == 'HighDiskUsage' and status == 'firing':
                    logging.info("HighDiskUsage alert firing. Running cleanup playbook.")
                    result = subprocess.run(
                        ["ansible-playbook", CLEANUP_PLAYBOOK_PATH],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    if result.returncode == 0:
                        logging.info("Cleanup playbook executed successfully.")
                    else:
                        logging.error(f"Cleanup playbook failed: {result.stderr}")

                # HighCPULoad logic
                if alertname == 'HighCPULoad':
                    if status == 'firing':
                        # Disable worker in Redis
                        logging.info(f"Disabling worker: {worker_name}")
                        result = subprocess.run(
                            ["python3", UPDATE_WORKERS_SCRIPT, worker_name, "disable"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        if result.returncode == 0:
                            logging.info(f"Worker {worker_name} disabled successfully.")
                        else:
                            logging.error(f"Failed to disable worker {worker_name}: {result.stderr}")

                    elif status == 'resolved':
                        # Re-enable worker in Redis
                        logging.info(f"Enabling worker: {worker_name}")
                        result = subprocess.run(
                            ["python3", UPDATE_WORKERS_SCRIPT, worker_name, "enable"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        if result.returncode == 0:
                            logging.info(f"Worker {worker_name} enabled successfully.")
                        else:
                            logging.error(f"Failed to enable worker {worker_name}: {result.stderr}")
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            logging.debug("Lock released.")
    
    return '', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
