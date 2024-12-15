#!/usr/bin/env python3
import redis
import sys
import json
import logging

# Configure logging
logging.basicConfig(
    filename='/opt/data_pipeline/update_disabled_workers.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Absolute path to your Ansible inventory.json
INVENTORY_PATH = "/home/almalinux/data-pipeline/ansible/inventories/inventory.json"

def get_redis_host():
    try:
        with open(INVENTORY_PATH, 'r') as f:
            inventory = json.load(f)
        redis_host = inventory['storagegroup']['hosts']['storage']['ansible_host']
        logging.info(f"Retrieved Redis host: {redis_host}")
        return redis_host
    except Exception as e:
        logging.error(f"Error reading inventory file: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) != 3:
        logging.error("Incorrect usage. Expected: python update_disabled_workers.py <worker_name> <disable|enable>")
        print("Usage: python update_disabled_workers.py <worker_name> <disable|enable>")
        sys.exit(1)
    
    worker_name = sys.argv[1]
    action = sys.argv[2]
    
    redis_host = get_redis_host()
    redis_port = 6379
    redis_db = 0
    
    try:
        r = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
        if action == 'disable':
            r.sadd('disabled_workers', worker_name)
            logging.info(f"Worker {worker_name} disabled.")
            print(f"Worker {worker_name} disabled.")
        elif action == 'enable':
            r.srem('disabled_workers', worker_name)
            logging.info(f"Worker {worker_name} enabled.")
            print(f"Worker {worker_name} enabled.")
        else:
            logging.error("Invalid action. Must be 'disable' or 'enable'.")
            print("Action must be 'disable' or 'enable'.")
            sys.exit(1)
    except Exception as e:
        logging.error(f"Redis connection error: {e}")
        print(f"Redis connection error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
