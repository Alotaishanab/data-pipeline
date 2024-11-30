# /opt/data_pipeline/celery_worker.py

from celery import Celery
import subprocess
import os

app = Celery('tasks', broker='redis://control-node:6379/0')  # Replace with actual Redis host

@app.task
def run_pipeline(pdb_file, results_dir):
    pipeline_script = "/opt/data_pipeline/pipeline_script.py"
    cmd = f"python3 {pipeline_script} {pdb_file} {results_dir}"
    process = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return {
        'stdout': process.stdout,
        'stderr': process.stderr,
        'returncode': process.returncode
    }
