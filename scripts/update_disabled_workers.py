#!/usr/bin/env python3
import redis
import sys

# Adjust the Redis connection details
redis_host = "localhost"  # or IP of your Redis server on the host/storage VM
redis_port = 6379
redis_db = 0

if len(sys.argv) != 3:
    print("Usage: python update_disabled_workers.py <worker_name> <disable|enable>")
    sys.exit(1)

worker_name = sys.argv[1]
action = sys.argv[2]

r = redis.Redis(host=redis_host, port=redis_port, db=redis_db)

if action == 'disable':
    r.sadd('disabled_workers', worker_name)
    print(f"Worker {worker_name} disabled.")
elif action == 'enable':
    r.srem('disabled_workers', worker_name)
    print(f"Worker {worker_name} enabled.")
else:
    print("Action must be 'disable' or 'enable'.")
    sys.exit(1)
