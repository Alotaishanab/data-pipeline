#!/usr/bin/env python3
from flask import Flask, request
import subprocess
import json

app = Flask(__name__)

# Adjust paths to match your actual directory structure
CLEANUP_PLAYBOOK_PATH = "../ansible/playbooks/cleanup_disk_space.yml"
UPDATE_WORKERS_SCRIPT = "./update_disabled_workers.py"

@app.route('/alertmanager-webhook', methods=['POST'])
def alertmanager_webhook():
    data = request.json
    if not data:
        return '', 200

    alerts = data.get('alerts', [])
    for alert in alerts:
        alertname = alert.get('labels', {}).get('alertname')
        status = alert.get('status')  # 'firing' or 'resolved'
        instance = alert.get('labels', {}).get('instance', 'unknown')

        if alertname == 'HighDiskUsage' and status == 'firing':
            # Run the cleanup disk space playbook
            subprocess.run(["ansible-playbook", "-i", "../ansible/inventories/inventory.json", CLEANUP_PLAYBOOK_PATH], check=False)

        if alertname == 'HighCPULoad':
            # Disable or enable worker based on alert status
            # Assume 'instance' corresponds to a worker name like 'worker1', 'worker2', etc.
            # If your instance label is a hostname:port, you may need to parse it.
            if status == 'firing':
                # Disable worker
                subprocess.run(["python3", UPDATE_WORKERS_SCRIPT, instance, "disable"], check=False)
            elif status == 'resolved':
                # Re-enable worker
                subprocess.run(["python3", UPDATE_WORKERS_SCRIPT, instance, "enable"], check=False)

    return '', 200

if __name__ == '__main__':
    # Run on port 8080, accessible to Alertmanager
    # Replace 0.0.0.0 with your host VM's IP if needed
    app.run(host='0.0.0.0', port=8080)
