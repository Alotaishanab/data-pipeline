tests/ansible/
Holds tests related to your Ansible playbooks and roles (Molecule or manual test playbooks).
tests/python/
Holds Python unit tests for scripts like pipeline_script.py, results_parser.py, or your Celery tasks.
tests/integration/
Holds end-to-end or system-level tests (e.g., verifying data moves from “input” to “output,” or that alerts get fired correctly).
tests/README.md
Explains how to run tests, dependencies, etc.




# Testing Framework for Alotaishanab Data Pipeline

## Overview

This directory contains tests for various components of the data pipeline, including Ansible playbooks, Python scripts, and integration scenarios.

## Structure

- **ansible/**: Contains playbook-based tests.
- **python/**: Contains unit tests for Python scripts.
- **integration/**: Contains end-to-end and system-level tests.

## Running Tests

### 1. Python Unit Tests

**Location:** `tests/python/`

**Run All Python Tests:**
```bash
pytest tests/python


# Ansible Playbook Tests

## Overview

This directory contains tests for various Ansible playbooks within the Alotaishanab-data-pipeline project. Each playbook has corresponding tests to ensure correct configuration and deployment.

## Playbooks Covered

- `common.yml`: Common configurations applicable to all machines.
- `install_dependencies.yml`: Installs dependencies on worker nodes.
- `nfsserver.yml`: Configures the NFS server.
- `nfsclients.yml`: Configures NFS clients.
- `download_and_prepare_datasets.yml`: Downloads and prepares datasets.
- `setup_symlinks.yml`: Sets up symbolic links for databases.

## Running Tests

### Execute All Playbook Tests

```bash
ansible-playbook -i localhost, --connection=local tests/ansible/test_playbooks.yml


# Ansible Playbook Tests

## Overview

This directory contains tests for various Ansible playbooks within the Alotaishanab-data-pipeline project. Each playbook has corresponding tests to ensure correct configuration and deployment.

## Playbooks Covered

- `common.yml`: Common configurations applicable to all machines.
- `install_dependencies.yml`: Installs dependencies on worker nodes.
- `nfsserver.yml`: Configures the NFS server.
- `nfsclients.yml`: Configures NFS clients.
- `download_and_prepare_datasets.yml`: Downloads and prepares datasets.
- `setup_symlinks.yml`: Sets up symbolic links for databases.
- `uncompress_files.yml`: Uncompresses `.pdb.gz` and `.cif.gz` files.
- `deploy_scripts.yml`: Deploys pipeline scripts to workers and host.
- `monitoring_and_logging.yml`: Sets up monitoring and logging on all hosts.
- `redis_setup.yml`: Sets up Redis server for Celery.
- `celery_setup.yml`: Sets up Celery workers.
- `setup_webhook_server.yml`: Sets up the webhook server and HTTP server for results.

## Running Tests

### Execute All Playbook Tests

```bash
ansible-playbook -i localhost, --connection=local tests/ansible/test_playbooks.yml
