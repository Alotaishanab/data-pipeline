#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Path to the Ansible inventory
INVENTORY="../../ansible/inventories/inventory.json"

# Path to the Ansible playbook
PLAYBOOK="../../ansible/playbooks/master_pipeline.yml"

if [ ! -f "$INVENTORY" ]; then
    echo "Error: Ansible inventory not found at $INVENTORY"
    exit 1
fi

if [ ! -f "$PLAYBOOK" ]; then
    echo "Error: Ansible playbook not found at $PLAYBOOK"
    exit 1
fi

echo "Running Ansible playbook: $PLAYBOOK with inventory: $INVENTORY"

ansible-playbook -i "$INVENTORY" "$PLAYBOOK"
