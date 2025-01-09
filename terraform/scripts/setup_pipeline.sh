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
            sudo apt-get update -y
            sudo apt-get install -y wget unzip git python3
        elif command -v yum &> /dev/null; then
            # For RHEL / CentOS / AlmaLinux / RockyLinux etc.
            sudo yum update -y

            # Enable EPEL first
            sudo yum install -y epel-release

            # Now you can install Ansible
            sudo yum install -y ansible wget unzip git python3

        else
            echo "Unsupported Linux package manager. Please install wget, unzip, git, python3, and ansible manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install wget unzip git python3 ansible
        if ! command -v jq &> /dev/null; then
            echo "jq not found. Installing jq..."
            brew install jq
        fi
    else
        echo "Unsupported OS. Please install wget, unzip, git, python3, and ansible manually."
        exit 1
    fi
}



run_terraform() {
    echo "Initializing Terraform..."
    terraform init

    echo "Applying Terraform configuration..."
    terraform apply -auto-approve
}

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

get_ssh_config() {
    echo "Fetching SSH configuration from Terraform output..."
    SSH_CONFIG=$(terraform output -raw ssh_config)
}

print_ssh_instructions() {
    echo ""
    echo "=============================================="
    echo "         SSH Access Instructions              "
    echo "=============================================="
    echo ""

    echo "You can SSH into your VMs using the following commands:"
    echo ""

    echo "$SSH_CONFIG" | awk '/^Host / {host=$2} /^    HostName / {print "ssh -i /home/almalinux/.ssh/ansible_ed25519" (ENVIRON["ON_CONDENSER"] == "true" ? "" : " -J condenser-proxy") " almalinux@"$2" # "host}'
    echo ""
    echo "You can also use your marker private key by replacing the path to the SSH key."
    echo ""
    echo "=============================================="
    
    echo "Note:"
    echo "- If you are on the condenser host, you do not need to use the '-J condenser-proxy' option."
    echo "- If you are not on the condenser host, include the '-J condenser-proxy' option to proxy your SSH connection."
    echo ""
    echo "Ensure that your SSH keys are correctly set up."
    echo ""
    echo "=============================================="
}


# Main script execution
install_packages        # <--- This now installs ansible as well
install_terraform

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

# After Terraform is done, generate the Ansible inventory
echo "Generating updated Ansible inventory from Terraform outputs..."
python3 scripts/generate_inventory.py --list

echo "Provisioning and setup complete."
echo "You can now SSH into the Host VM using the instructions above."


echo "------------------------------------------"
echo "Running Ansible playbook to copy the local ansible_ed25519 to mgmt node..."

cd ../ansible || { echo "Failed to cd into ../ansible"; exit 1; }

ansible-playbook \
  -i inventories/inventory.json \
  playbooks/copy_local_files.yml \
  --private-key=~/.ssh/ansible_ed25519

echo "Playbook complete. The mgmt node now has /home/almalinux/.ssh/ansible_ed25519"
echo "------------------------------------------"

cd ../terraform
echo "Done."
