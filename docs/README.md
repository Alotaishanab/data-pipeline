## **Table of Contents**

1. [Understanding the Requirements](#1-understanding-the-requirements)
2. [Planning the Infrastructure](#2-planning-the-infrastructure)
3. [Setting Up the Cloud Machines](#3-setting-up-the-cloud-machines)
4. [Configuring the Machines](#4-configuring-the-machines)
5. [Setting Up Data Storage](#5-setting-up-data-storage)
6. [Installing Dependencies and Software](#6-installing-dependencies-and-software)
7. [Configuring the Data Analysis Pipeline](#7-configuring-the-data-analysis-pipeline)
8. [Automating the Workflow](#8-automating-the-workflow)
9. [Running the Pipeline](#9-running-the-pipeline)
10. [Collecting and Aggregating Results](#10-collecting-and-aggregating-results)
11. [Setting Up Monitoring and Logging](#11-setting-up-monitoring-and-logging)
12. [Providing Access to Results](#12-providing-access-to-results)
13. [Writing the Report](#13-writing-the-report)
14. [Final Checks and Deliverables](#14-final-checks-and-deliverables)

---

### **1. Understanding the Requirements**

Before diving into implementation, it's crucial to fully understand the project's requirements:

- **Objective**: Build a distributed data analysis pipeline that processes large protein datasets using the provided `pipeline_script.py` and `results_parser.py`.
- **Resources**: Utilize 4 or 5 cloud machines with specified configurations.
- **Deliverables**:
  - A report (max 4,000 words) explaining your design and choices.
  - A GitHub repository with all code and instructions.
  - Running instances of your system accessible via provided IPs.

### **2. Planning the Infrastructure**

Determine how you'll use your available machines:

- **Host Machine**:
  - **Role**: Orchestrates tasks, runs configuration management tools, provides access to results.
  - **Specs**: 1 CPU, 4GB RAM, 10GB HDD.

- **Worker Machines** (3 machines):
  - **Role**: Execute the data analysis pipeline.
  - **Specs**: 4 CPUs, 32GB RAM, 25GB HDD each.

- **Optional Storage Machine**:
  - **Role**: Centralized storage for datasets and results.
  - **Specs**: 4 CPUs, 8GB RAM, 10GB primary HDD, 200GB secondary HDD.

**Decisions to Make**:

- **Configuration Management Tool**: Choose between Ansible, SaltStack, etc.
  - **Recommendation**: **Ansible**, due to its simplicity and agentless architecture.

- **Data Storage Solution**: Decide on how to store and share datasets and results.
  - **Options**:
    - Network File System (NFS).
    - Distributed file systems like GlusterFS.
  - **Recommendation**: **NFS**, as it's suitable for small clusters and easier to set up.

### **3. Setting Up the Cloud Machines**

- **Provision Machines**:
  - Use Condenser to create your VMs with the specified configurations.
  - Assign static IP addresses for consistent access.

- **Access Setup**:
  - Generate SSH keys for secure communication.
  - Install the provided `lecturer_key.pub` on the host machine for grader access.

### **4. Configuring the Machines**

- **Install Ansible on Host**:
  - Configure Ansible to manage worker (and storage) machines.
  - Set up inventory files with machine IPs and roles.

- **Set Up SSH Access**:
  - Ensure the host machine can SSH into workers without a password.
  - Distribute SSH public keys to worker machines.

### **5. Setting Up Data Storage**

- **Option 1: NFS Server on Storage Machine**:
  - Install NFS server on the storage machine.
  - Export directories for datasets and results.
  - Mount NFS shares on worker and host machines.

- **Option 2: NFS Server on Host Machine** (if not using a storage machine):
  - Similar setup as above but hosted on the host machine.

- **Permissions**:
  - Set appropriate read/write permissions for shared directories.

### **6. Installing Dependencies and Software**

- **Use Ansible Playbooks**:
  - Create playbooks to automate installation of required software.

- **Install Python and Pip**:
  - Ensure Python 3.x is installed on all machines.
  - Install `pip` for package management.

- **Install Python Packages**:
  - `biopython`
  - `torch`
  - `numpy`
  - `scipy`
  - `faiss-cpu`

- **Install Merizo Search**:
  - Clone the repository from GitHub.
  - Follow installation instructions provided in the repo.

- **Set Up Virtual Environments** (optional but recommended):
  - Use `venv` or `conda` to manage dependencies.

### **7. Configuring the Data Analysis Pipeline**

- **Obtain Pipeline Scripts**:
  - Place `pipeline_script.py` and `results_parser.py` in a shared directory accessible by workers.

- **Download Datasets**:
  - **Human Proteome**:
    - Download `UP000005640_9606_HUMAN_v4.tar` directly to the storage or host machine.
  - **E.coli Proteome**:
    - Download `UP000000625_83333_ECOLI_v4.tar` similarly.
  - **CATH Foldclass DB**:
    - Download `cath_foldclassdb.tar.gz`.

- **Extract Datasets**:
  - Use `tar` to extract datasets to designated directories.

- **Ensure Access**:
  - Verify that worker machines can access datasets via mounted NFS shares.

### **8. Automating the Workflow**

- **Task Distribution**:
  - Decide how to distribute tasks across workers.
  - **Options**:
    - Use a simple queuing system with shared directories.
    - Implement a job scheduler (e.g., `celery`, `RabbitMQ`).
    - Use GNU Parallel for task execution.

- **Recommendation**:
  - For simplicity, use a custom Python script that assigns tasks to workers based on available resources.

- **Load Balancing**:
  - Ensure tasks are evenly distributed to prevent overloading any single worker.

### **9. Running the Pipeline**

- **Testing**:
  - Run the pipeline on a small subset (e.g., test files) to ensure everything works.

- **Execution**:
  - Start the pipeline across all worker machines.
  - Monitor CPU and memory usage.

- **Resource Management**:
  - Limit the number of concurrent processes on each worker to prevent resource exhaustion.

### **10. Collecting and Aggregating Results**

- **Store Intermediate Outputs**:
  - Ensure all `.tsv` and `.parsed` files are saved in a designated results directory.

- **Aggregation Scripts**:
  - Write scripts to parse all `.parsed` files and generate:
    - `human_cath_summary.csv`
    - `ecoli_cath_summary.csv`
    - `plDDT_means.csv`

- **Verify Results**:
  - Check that the summary files match the expected format.

### **11. Setting Up Monitoring and Logging**

- **Monitoring Tools**:
  - Install tools like `htop`, `nmon`, or set up more advanced monitoring with Prometheus and Grafana.

- **Logging**:
  - Configure logs for:
    - Pipeline execution (stdout and stderr).
    - System performance metrics.

- **Alerts**:
  - Optionally, set up email or messaging alerts for failures or high resource usage.

### **12. Providing Access to Results**

- **Web Server Setup**:
  - Install a web server (e.g., Apache, Nginx) on the host or storage machine.

- **Serve Results Directory**:
  - Configure the web server to serve the results directory over HTTP or HTTPS.

- **Security**:
  - Implement basic authentication if necessary.
  - Secure the server with SSL certificates.

- **Alternate Access Methods**:
  - Provide SFTP or SCP access if preferred.

### **13. Writing the Report**

- **Structure**:
  - **Introduction**:
    - Brief overview of the project and objectives.
  - **Design Choices**:
    - Explain the selection of Ansible for configuration management.
    - Justify the choice of NFS for data storage.
    - Describe how task distribution is handled.
    - Discuss the monitoring and logging setup.
  - **Implementation Details**:
    - Provide specifics on how the system was set up.
    - Include challenges faced and how they were overcome.
  - **Scalability Analysis**:
    - Evaluate how the system performs with larger datasets.
    - Identify bottlenecks and suggest improvements.
  - **Future Work**:
    - Propose enhancements for scalability and efficiency.
  - **Conclusion**:
    - Summarize findings and reflect on the project.

- **Include Required Information**:
  - GitHub repository link.
  - IP addresses and identities of the machines.
  - Instructions on how to access the results.

- **Word Limit**:
  - Ensure the report does not exceed 4,000 words.

### **14. Final Checks and Deliverables**

- **Testing**:
  - Simulate a fresh deployment using your GitHub repository to ensure instructions are complete.
  - Verify that the lecturer's key allows access as intended.

- **GitHub Repository**:
  - Ensure all code, scripts, and configuration files are committed.
  - Update the README with clear setup and usage instructions.

- **Results Accessibility**:
  - Confirm that the researchers can access the results as specified.

- **Documentation**:
  - Double-check that all deliverables meet the requirements.

---

## **Additional Considerations**

- **Scalability**:
  - Discuss in your report how the system can handle larger datasets or more organisms.
  - Consider the limitations imposed by the hardware and how you might address them (e.g., adding more workers, optimizing code).

- **Data Transfer and Storage**:
  - Be mindful of the time required to download large datasets.
  - Ensure there's enough disk space on the storage machine.

- **Security**:
  - Keep all software up to date to mitigate vulnerabilities.
  - Use firewalls to restrict access to necessary ports only.

- **Backup**:
  - Implement a backup strategy for critical data and results.






