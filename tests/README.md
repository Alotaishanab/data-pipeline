# Testing Framework for Data Pipeline


**Note:** Do not run the tests until the master pipeline has been executed and pipeline processing has been initiated.

## Overview

This directory contains comprehensive tests for the various components of the Data Pipeline. The tests ensure the reliability, correctness, and robustness of infrastructure provisioning, configuration management, data processing scripts, and the overall pipeline functionality.

## Testing Categories

### 1. Ansible Playbook Tests

**Location:** `tests/ansible/`

**Description:**  
Tests for verifying the correctness and reliability of Ansible playbooks. These tests ensure that playbooks correctly configure and deploy the necessary infrastructure and services.

**Playbooks Covered:**
- `common.yml`: Common configurations applicable to all machines.
- `install_dependencies.yml`: Installs dependencies on worker nodes.
- `nfs_server.yml`: Configures the NFS server.
- `nfs_clients.yml`: Configures NFS clients.
- `download_and_prepare_datasets.yml`: Downloads and prepares datasets.
- `setup_symlinks.yml`: Sets up symbolic links for databases.
- `uncompress_files.yml`: Uncompresses `.pdb.gz` and `.cif.gz` files.
- `deploy_scripts.yml`: Deploys pipeline scripts to workers and host.
- `monitoring_and_logging.yml`: Sets up monitoring and logging on all hosts.
- `redis_setup.yml`: Sets up Redis server for Celery.
- `celery_setup.yml`: Sets up Celery workers.
- `setup_webhook_server.yml`: Sets up the webhook server and HTTP server for results.

**Running Ansible Playbook Tests:**

1. **Execute All Playbook Tests:**
    ```bash
    ansible-playbook -i localhost, --connection=local tests/ansible/test_playbooks.yml
    ```

2. **Execute End-to-End Playbook Test:**
    ```bash
    ansible-playbook -i ../../ansible/inventories/inventory.json tests/integration/test_end_to_end.yml --private-key ~/.ssh/ansible_ed25519
    ```

### 2. Python Unit Tests

**Location:** `tests/python/`

**Description:**  
Unit tests for Python scripts such as `pipeline_script.py`, `results_parser.py`, and Celery tasks. These tests validate the functionality and correctness of individual components.

**Running Python Unit Tests:**

1. **Install Dependencies:**
    Ensure that all required Python packages are installed. From the root directory, run:
    ```bash
    pip install -r requirements.txt
    ```

2. **Run All Python Tests:**
    ```bash
    pytest tests/python/
    ```

### 3. Integration Tests

**Location:** `tests/integration/`

**Description:**  
End-to-end and system-level tests that verify the entire pipeline's functionality, including data flow from input to output and the triggering of alerts.

**Running Integration Tests:**

1. **Ensure Infrastructure is Provisioned and Configured:**
    Make sure that Terraform and Ansible have successfully provisioned and configured the infrastructure.

2. **Execute Integration Tests:**
    ```bash
    ansible-playbook -i ../../ansible/inventories/inventory.json tests/integration/test_end_to_end.yml --private-key ~/.ssh/ansible_ed25519
    ```

## Running All Tests

To run all tests in their respective categories, follow the steps below:

1. **Navigate to the Tests Directory:**
    ```bash
    cd tests
    ```

2. **Run Ansible Playbook Tests:**
    ```bash
    ansible-playbook -i localhost, --connection=local ansible/test_playbooks.yml
    ansible-playbook -i ../ansible/inventories/inventory.json integration/test_end_to_end.yml --private-key ~/.ssh/ansible_ed25519
    ```

3. **Run Python Unit Tests:**
    ```bash
    pip install -r ../requirements.txt
    pytest python/
    ```

## Dependencies

- **Ansible:** Ensure Ansible is installed and configured properly.
- **Terraform:** Required for infrastructure provisioning.
- **Python 3:** Necessary for running Python scripts and tests.
- **Pip Packages:** Install required Python packages using the provided `requirements.txt`.
    ```bash
    pip install -r requirements.txt
    ```



## Conclusion

The testing framework for the Alotaishanab Data Pipeline is designed to ensure that all components work seamlessly together, providing a reliable and efficient data analysis system. By following the structured approach outlined above, developers and operators can maintain high-quality standards and swiftly identify and resolve any issues that arise.
