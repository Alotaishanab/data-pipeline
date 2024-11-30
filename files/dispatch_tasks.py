# /opt/data_pipeline/dispatch_tasks.py

import sys
from celery_worker import run_pipeline

if __name__ == "__main__":
    pdb_file = sys.argv[1]
    results_dir = sys.argv[2]
    result = run_pipeline.delay(pdb_file, results_dir)
    print(f"Task {result.id} dispatched for {pdb_file}")
