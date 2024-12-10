#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Function to install Terraform
install_terraform() {
    if ! command -v terraform &> /dev/null
    then
        echo "Terraform not found. Installing Terraform..."
        # Detect OS and install accordingly
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Linux
            TERRAFORM_VERSION="1.10.1"
            wget https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip
            unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip
            sudo mv terraform /usr/local/bin/
            rm -f terraform_${TERRAFORM_VERSION}_linux_amd64.zip
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            TERRAFORM_VERSION="1.10.1"
            brew tap hashicorp/tap
            brew install hashicorp/tap/terraform
        else
            echo "Unsupported OS. Please install Terraform manually."
            exit 1
        fi
    else
        echo "Terraform is already installed."
    fi
}

# Function to install required packages
install_packages() {
    echo "Installing required packages..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get update -y && sudo apt-get install -y wget unzip git python3
        elif command -v yum &> /dev/null; then
            sudo yum update -y && sudo yum install -y wget unzip git python3
        else
            echo "Unsupported Linux package manager. Please install wget, unzip, git, and python3 manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew update
        brew install wget unzip git python3
    else
        echo "Unsupported OS. Please install wget, unzip, git, and python3 manually."
        exit 1
    fi
}

# Function to run Terraform
run_terraform() {
    echo "Initializing Terraform..."
    terraform init

    echo "Applying Terraform configuration..."
    terraform apply -auto-approve
}

# Function to generate placeholder files for CertificateFile and IdentityFile
generate_placeholder_files() {
    CONDENSER_CERT_FILE=~/.ssh/id_arc_rsa.signed
    CONDENSER_IDENTITY_FILE=~/.ssh/id_rsa

    if [ ! -f "$CONDENSER_CERT_FILE" ]; then
        echo "Generating placeholder for CertificateFile at $CONDENSER_CERT_FILE..."
        touch "$CONDENSER_CERT_FILE"
        echo "# Placeholder for CertificateFile. Please add your CertificateFile here." > "$CONDENSER_CERT_FILE"
        chmod 600 "$CONDENSER_CERT_FILE"
        echo "Please edit $CONDENSER_CERT_FILE and add your CertificateFile."
    fi

    if [ ! -f "$CONDENSER_IDENTITY_FILE" ]; then
        echo "Generating placeholder for IdentityFile at $CONDENSER_IDENTITY_FILE..."
        touch "$CONDENSER_IDENTITY_FILE"
        echo "# Placeholder for IdentityFile. Please add your IdentityFile here." > "$CONDENSER_IDENTITY_FILE"
        chmod 600 "$CONDENSER_IDENTITY_FILE"
        echo "Please edit $CONDENSER_IDENTITY_FILE and add your IdentityFile."
    fi
}

# Function to retrieve Terraform SSH Config Output
get_ssh_config() {
    echo "Fetching SSH configuration from Terraform output..."
    SSH_CONFIG=$(terraform output -raw ssh_config)
}

# Function to print SSH Instructions
print_ssh_instructions() {
    echo ""
    echo "=============================================="
    echo "         SSH Access Instructions              "
    echo "=============================================="
    echo ""
    echo "You can SSH into your VMs using the following commands:"
    echo ""

    # Extract VM entries from SSH_CONFIG
    echo "$SSH_CONFIG" | awk '/^Host / {host=$2} /^    HostName / {print "ssh -J condenser-proxy almalinux@"$2" # "host}' 

    echo ""
    echo "Alternatively, you can SSH directly using the IP addresses with ProxyJump:"
    echo ""
    echo "Example Commands:"
    echo "  ssh -J condenser-proxy almalinux@10.134.12.125  # Host Machine"
    echo "  ssh -J condenser-proxy almalinux@10.134.12.87   # Worker1"
    echo "  ssh -J condenser-proxy almalinux@10.134.12.121  # Worker2"
    echo "  ssh -J condenser-proxy almalinux@10.134.12.93   # Worker3"
    echo "  ssh -J condenser-proxy almalinux@10.134.12.141  # Storage Machine"
    echo ""
    echo "Ensure that your SSH keys are correctly set up and that the public key (~/.ssh/id_rsa.pub) is added to the ~/.ssh/authorized_keys on each VM."
    echo ""
    echo "If you encounter any issues, please contact your system administrator."
    echo ""
    echo "=============================================="
}

# Function to generate Ansible Inventory
generate_ansible_inventory() {
    echo "Generating Ansible inventory..."
    # Path to the generate_inventory.py script
    INVENTORY_SCRIPT="../../ansible/inventories/generate_inventory.py"
    # Output path for inventory.json
    INVENTORY_OUTPUT="../../ansible/inventories/inventory.json"

    if [ ! -f "$INVENTORY_SCRIPT" ]; then
        echo "Error: Inventory script not found at $INVENTORY_SCRIPT"
        exit 1
    fi

    # Make sure the script is executable
    chmod +x "$INVENTORY_SCRIPT"

    # Run the inventory script and output to inventory.json
    python3 "$INVENTORY_SCRIPT" --list > "$INVENTORY_OUTPUT"

    echo "Ansible inventory generated at $INVENTORY_OUTPUT"
}

# Function to run Ansible Playbooks
run_ansible_playbooks() {
    echo "Running Ansible playbooks..."
    # Path to the run_ansible.sh script
    ANSIBLE_SCRIPT="../../scripts/run_ansible.sh"

    if [ ! -f "$ANSIBLE_SCRIPT" ]; then
        echo "Error: Ansible script not found at $ANSIBLE_SCRIPT"
        exit 1
    fi

    # Make sure the script is executable
    chmod +x "$ANSIBLE_SCRIPT"

    # Run the Ansible playbooks
    "$ANSIBLE_SCRIPT"

    echo "Ansible playbooks executed successfully."
}

# Main script execution
install_packages
install_terraform

# Generate placeholder files for condenser-proxy if needed
generate_placeholder_files

# Change directory to the terraform directory
echo "Changing directory to the terraform directory..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$(dirname "$SCRIPT_DIR")"

echo "Terraform directory resolved to: $TERRAFORM_DIR"
cd "$TERRAFORM_DIR" || { echo "Failed to change directory to $TERRAFORM_DIR"; exit 1; }

echo "Current directory: $(pwd)"
echo "Listing Terraform directory contents:"
ls -la

# Run Terraform to provision VMs
run_terraform

# Retrieve and display SSH config
get_ssh_config
print_ssh_instructions

# Generate Ansible Inventory
generate_ansible_inventory

# Run Ansible Playbooks to configure VMs
run_ansible_playbooks

echo "Setup complete."
