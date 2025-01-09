# Data Pipeline Deployment Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Setup Instructions](#setup-instructions)
    - [1. Install Git](#1-install-git)
    - [2. Clone the Repository](#2-clone-the-repository)
    - [3. Configure Terraform Variables](#3-configure-terraform-variables)
    - [4. Deploy the Pipeline Setup Script](#4-deploy-the-pipeline-setup-script)
4. [Ansible Inventory Configuration](#ansible-inventory-configuration)
5. [Deploying with Ansible](#deploying-with-ansible)
    - [1. SSH into the Host Node](#1-ssh-into-the-host-node)
    - [2. Run the Ansible Playbook](#2-run-the-ansible-playbook)
6. [Accessing Monitoring Services](#accessing-monitoring-services)
    - [Prometheus](#prometheus)
    - [Grafana](#grafana)
    - [Node Exporter](#node-exporter)
    - [Web Server](#web-server)
7. [Grafana Credentials](#grafana-credentials)
8. [Ansible Inventory Details](#ansible-inventory-details)
9. [Testing the Pipeline](#testing-the-pipeline)
    - [1. Test Ansible Playbooks](#1-test-ansible-playbooks)
    - [2. Test End-to-End Integration](#2-test-end-to-end-integration)
    - [3. Test Python Scripts](#3-test-python-scripts)

---

## Introduction

This guide provides step-by-step instructions to set up and deploy the **Data Pipeline** using Terraform and Ansible. It covers configuration, provisioning of machines, deployment of services, and testing to ensure everything functions as expected.

## Prerequisites

### Local Machine

- **Operating System:** Linux-based OS
- **SSH Access:** Ensure you have SSH access with the necessary private keys.
- **Terraform:** Installed on your local machine.
- **Ansible:** Installed on the host node.
- **Python 3:** Installed on all relevant machines.
- **Necessary Permissions:** Ensure you have the required permissions to execute scripts and manage services on the target machines.

### Remote Machines

- **SSH Keys:** Ensure that the `ansible_ed25519` key is installed on the VM you're using.
- **Network Access:** Ensure that all machines can communicate with each other and with the Redis broker.

## Setup Instructions

### 1. Install Git

Begin by installing Git on your local machine to clone the repository.

```bash
sudo dnf install git -y
```

### 2. Clone the Repository

Clone the Data Pipeline repository from GitHub:

```bash
git clone https://github.com/Alotaishanab/data-pipeline.git
cd data-pipeline/terraform/scripts
```

### 3. Configure Terraform Variables

Before provisioning the machines, you need to configure your Terraform variables.

#### Edit Terraform Variables File

Open the `terraform.tfvars` file located at `/data-pipeline/terraform/terraform.tfvars`:

```bash
nano /data-pipeline/terraform/terraform.tfvars
```

#### Add Required Variables

Insert the following variables with your specific values:

```hcl
provider_token       = "YOUR_PROVIDER_TOKEN"
provider_namespace   = "YOUR_PROVIDER_NAMESPACE"
username             = "YOUR_USERNAME"
network_name         = "YOUR_NETWORK_NAME"
```

#### Update Cloud Configuration

Navigate to the cloud configuration template and add your token:

```bash
nano /data-pipeline/terraform/templates/cloud-config.yaml
```

Insert your token in the designated section as per the template's instructions.

### 4. Deploy the Pipeline Setup Script

Make the `setup_pipeline.sh` script executable and run it to provision the machines:

```bash
sudo chmod +x setup_pipeline.sh
./setup_pipeline.sh
```

## Ansible Inventory Configuration

The Ansible inventory has been updated with the new IPs of the freshly provisioned machines. Ensure that the SSH keys are correctly set up to allow Ansible to communicate with these hosts.

## Deploying with Ansible

### 1. SSH into the Host Node

Use your marker’s private key or the `ansible_ed25519` key installed on the VM you are using to SSH into the host node:

```bash
ssh -i ~/.ssh/ansible_ed25519 almalinux@<HOST_IP_ADDRESS>
```

**Note:** Replace `<HOST_IP_ADDRESS>` with the actual IP address of your host node.

#### Using the Proxy Jump (-J) Option

If you're accessing the host node through the condenser-proxy, use the `-J` option as shown:

```bash
ssh -i ~/.ssh/ansible_ed25519 -J condenser-proxy almalinux@<HOST_IP_ADDRESS>
```

### 2. Run the Ansible Playbook

Once you're on the host node, navigate to the Ansible directory and run the playbook to deploy the data pipeline:

```bash
cd data-pipeline/ansible
ansible-playbook -i /home/almalinux/data-pipeline/ansible/inventories/inventory.json /home/almalinux/data-pipeline/ansible/playbooks/master_pipeline.yml
```

## Accessing Monitoring Services

After deployment, you can access the monitoring services using the following URLs. Replace `<USERNAME>` with your specific username:

- **Prometheus:** https://<USERNAME>-promethh.comp0235.condenser.arc.ucl.ac.uk/
- **Grafana:** https://<USERNAME>-grafann.comp0235.condenser.arc.ucl.ac.uk/
- **Node Exporter:** https://<USERNAME>-nodeexportt.comp0235.condenser.arc.ucl.ac.uk/
- **Web Server:** https://<USERNAME>-webserv.comp0235.condenser.arc.ucl.ac.uk/

## Grafana Credentials

- **Username:** `admin`
- **Password:** `admin`

**Security Note:** It is highly recommended to change the default Grafana credentials after the initial setup to secure your monitoring dashboards.

## Ansible Inventory Details

Below is the structure of your Ansible inventory. Ensure that the IP addresses and hostnames match your current environment:

```json
{
    "all": {
        "children": {
            "mgmtnode": {},
            "workers": {},
            "storagegroup": {}
        }
    },
    "mgmtnode": {
        "hosts": {
            "host": {
                "ansible_host": "10.134.12.255"
            }
        }
    },
    "workers": {
        "hosts": {
            "worker1": {
                "ansible_host": "10.134.13.5"
            },
            "worker2": {
                "ansible_host": "10.134.12.252"
            },
            "worker3": {
                "ansible_host": "10.134.12.189"
            }
        }
    },
    "storagegroup": {
        "hosts": {
            "storage": {
                "ansible_host": "10.134.12.215"
            }
        }
    }
}
```

**Note:** Update the `inventory.json` file with the IP addresses of your machines as needed.

## Testing the Pipeline

### 1. Test Ansible Playbooks

To verify that the Ansible playbooks are functioning correctly, run the following command:

```bash
cd data-pipeline
ansible-playbook -i localhost, --connection=local tests/ansible/test_playbooks.yml
```

### 2. Test End-to-End Integration

For end-to-end integration testing of the pipeline, execute:

```bash
cd /data-pipeline/tests/integration
ansible-playbook -i ../../ansible/inventories/inventory.json test_end_to_end.yml --private-key ~/.ssh/ansible_ed25519
```

### 3. Test Python Scripts

To test the Python scripts involved in the pipeline, use the following command to count the number of `.parsed` files in the results directory:

```bash
cd /data-pipeline/tests/python
find /mnt/results -type f -name "*.parsed" | wc -l
```

## Additional Configuration Steps

### Steps to Configure and Provision Machines

#### Update Terraform Variables

Navigate to the file located at `/data-pipeline/terraform/terraform.tfvars` and add the following details:

- `provider_token`
- `provider_namespace`
- `username`
- `network_name`

#### Configure Cloud Settings

Open the template file at `/data-pipeline/terraform/templates/cloud-config.yaml` and insert your specific token in the designated section.

#### Provision the Machines

After completing the above configurations, proceed to provision the machines using your Terraform setup.

### Summary

**File Paths to Edit:**

- `/data-pipeline/terraform/terraform.tfvars`: Add `provider_token`, `provider_namespace`, `username`, and `network_name`.
- `/data-pipeline/terraform/templates/cloud-config.yaml`: Insert your token.

Ensure all necessary information is correctly added to these files before initiating the provisioning process to successfully set up your machines.

