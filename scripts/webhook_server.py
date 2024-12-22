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
CLEANUP_PLAYBOOK_PATH = "/home/almalinux/data-pipeline/ansible/playbooks/cleanup_disk_space.yml"  # Update path if needed
UPDATE_WORKERS_SCRIPT = "/opt/data_pipeline/update_disabled_workers.py"  # Update path if needed


def disable_celery_worker(worker_name):
    """
    Disables a Celery worker gracefully using celery control commands.
    """
    try:
        # Construct the celery control command
        celery_command = [
            "celery",
            "-A", "celery_worker",  # Replace with your Celery app name if different
            "control",
            "shutdown",
            "-d", worker_name,  # Destination worker name
            "--soft",          # Graceful shutdown
            "--timeout=30"     # Optional timeout in seconds
        ]

        # Execute the command
        process = subprocess.run(celery_command, capture_output=True, text=True, check=False)

        if process.returncode == 0:
            logging.info(f"Successfully sent shutdown signal to Celery worker {worker_name}")
            logging.debug(f"Celery control stdout: {process.stdout}")
        else:
            logging.error(f"Failed to send shutdown signal to Celery worker {worker_name}")
            logging.error(f"Celery control stderr: {process.stderr}")

    except Exception as e:
        logging.error(f"Exception occurred while disabling Celery worker {worker_name}: {e}")


def enable_celery_worker(worker_name):
    """
    Enables a Celery worker by starting the Celery service.
    """
    manage_celery_service(worker_name, 'start')


def manage_celery_service(worker_name, action):
    """
    Manage the Celery service on the specified worker using Ansible ad-hoc commands.
    """
    if action not in ['start', 'stop']:
        logging.error(f"Invalid action '{action}' for managing Celery service.")
        return

    logging.info(f"Attempting to {action} Celery service on worker: {worker_name}")

    ansible_command = [
        "ansible",
        worker_name,
        "-i", INVENTORY_PATH,
        "-m", "systemd",
        "-a", f"name=celery state={'started' if action == 'start' else 'stopped'}"
    ]

    try:
        process = subprocess.run(
            ansible_command,
            capture_output=True,
            text=True,
            check=False
        )

        if process.returncode == 0:
            logging.info(f"Successfully {action}ed Celery service on {worker_name}.")
            logging.debug(f"Ansible stdout: {process.stdout}")
        else:
            logging.error(f"Failed to {action} Celery service on {worker_name}. Return code: {process.returncode}")
            logging.error(f"Ansible stderr: {process.stderr}")
    except Exception as e:
        logging.error(f"Exception occurred while trying to {action} Celery service on {worker_name}: {e}")


def is_celery_running(worker_name):
    """
    Checks if Celery service is active (running) on the given worker.
    """
    ansible_command = [
        "ansible",
        worker_name,
        "-i", INVENTORY_PATH,
        "-m", "command",
        "-a", "systemctl is-active celery"
    ]
    process = subprocess.run(ansible_command, capture_output=True, text=True, check=False)
    if process.returncode == 0 and process.stdout.strip() == "active":
        return True
    return False


def is_celery_stopped(worker_name):
    """
    Checks if Celery service is stopped (not active) on the given worker.
    """
    ansible_command = [
        "ansible",
        worker_name,
        "-i", INVENTORY_PATH,
        "-m", "command",
        "-a", "systemctl is-active celery"
    ]
    process = subprocess.run(ansible_command, capture_output=True, text=True, check=False)
    # If return code != 0 or output != "active", consider it stopped
    if process.returncode != 0 or process.stdout.strip() != "active":
        return True
    return False


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
            try:
                process = subprocess.run([
                    "ansible-playbook",
                    "-vvvv",
                    "-i", INVENTORY_PATH,
                    "--limit", worker_name,
                    "--become",
                    CLEANUP_PLAYBOOK_PATH
                ], capture_output=True, text=True, check=True)  # check=True to raise CalledProcessError

                logging.info(f"Executed cleanup_disk_space.yml playbook.")
                logging.debug(f"Cleanup stdout: {process.stdout}")
                if process.returncode != 0:
                    logging.error(f"Cleanup stderr: {process.stderr}")
                logging.info(f"Cleanup returncode: {process.returncode}")
            except subprocess.CalledProcessError as e:
                logging.error(f"Error running cleanup playbook: {e}")
                logging.error(f"Cleanup stderr: {e.stderr}")

        if alertname == 'HighCPULoad':
            if status == 'firing':
                logging.info(f"HighCPULoad alert firing for worker: {worker_name} - Disabling worker")

                # Disable worker in Redis
                try:
                    process = subprocess.run([
                        "python3",
                        UPDATE_WORKERS_SCRIPT,
                        worker_name,
                        "disable"
                    ], capture_output=True, text=True, check=True)  # check=True to raise CalledProcessError

                    logging.info(f"Executed update_disabled_workers.py to disable {worker_name}.")
                    logging.debug(f"Disable stdout: {process.stdout}")
                    if process.returncode != 0:
                        logging.error(f"Disable stderr: {process.stderr}")
                    logging.info(f"Disable returncode: {process.returncode}")
                except subprocess.CalledProcessError as e:
                    logging.error(f"Error disabling worker in Redis: {e}")
                    logging.error(f"Disable stderr: {e.stderr}")

                # Gracefully shut down the Celery worker
                disable_celery_worker(worker_name)

            elif status == 'resolved':
                logging.info(f"HighCPULoad alert resolved for worker: {worker_name} - Enabling worker")

                # Enable worker in Redis
                try:
                    process = subprocess.run([
                        "python3",
                        UPDATE_WORKERS_SCRIPT,
                        worker_name,
                        "enable"
                    ], capture_output=True, text=True, check=True)  # check=True to raise CalledProcessError

                    logging.info(f"Executed update_disabled_workers.py to enable {worker_name}.")
                    logging.debug(f"Enable stdout: {process.stdout}")
                    if process.returncode != 0:
                        logging.error(f"Enable stderr: {process.stderr}")
                    logging.info(f"Enable returncode: {process.returncode}")
                except subprocess.CalledProcessError as e:
                    logging.error(f"Error enabling worker in Redis: {e}")
                    logging.error(f"Enable stderr: {e.stderr}")

                # Start the Celery service to enable the worker
                enable_celery_worker(worker_name)

    return '', 200


if __name__ == '__main__':
    # Run on port 8080, accessible to Alertmanager
    app.run(host='0.0.0.0', port=8080)