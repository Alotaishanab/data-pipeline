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

# Function to install required packages without updating Homebrew
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
        # Removed brew update to prevent extensive upgrades
        brew install wget unzip git python3

        # Ensure jq is installed for JSON parsing in SSH instructions
        if ! command -v jq &> /dev/null; then
            echo "jq not found. Installing jq..."
            brew install jq
        fi
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
    echo "Ensure that your SSH keys are correctly set up and that the public key (~/.ssh/id_rsa.pub) is added to the ~/.ssh/authorized_keys on each VM."
    echo ""
    echo "If you encounter any issues, please contact your system administrator."
    echo ""
    echo "=============================================="
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

echo "Provisioning and setup complete."
echo "You can now SSH into the Host VM using the instructions above."