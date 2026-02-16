# PetClinic Azure Deployment

Automated deployment of a **3-tier Spring PetClinic application** on Azure using Python and Azure CLI. One command provisions the entire infrastructure from scratch and deploys the application.

## Architecture

```
                    Internet
                       |
               [ Azure VNet 10.0.0.0/16 ]
                       |
          +--------------------------+
          |    Frontend Subnet       |
          |      10.0.1.0/24         |
          |                          |
          |  +--------------------+  |
          |  | Frontend VM        |  |
          |  | Nginx + Angular    |  |
          |  | :80 (public)       |  |
          |  +--------------------+  |
          +-----------|--------------+
                      |
          +-----------|--------------+
          |    Backend Subnet        |
          |      10.0.2.0/24         |
          |                          |
          |  +--------------------+  |   +--------------------+
          |  | Backend VM         |  |   | Database VM        |
          |  | Spring Boot REST   |--|---| MySQL 8.0          |
          |  | :9966              |  |   | :3306              |
          |  +--------------------+  |   +--------------------+
          |                          |
          +--------------------------+
```

**Traffic flow:** User &rarr; Nginx (:80) &rarr; reverse proxy &rarr; Spring Boot (:9966) &rarr; MySQL (:3306)

## What it does

The deployment tool performs the following steps automatically:

1. **Preflight check** &mdash; verifies Azure CLI is installed and authenticated
2. **Resource Group** &mdash; creates a dedicated resource group
3. **Network stack** &mdash; VNet, subnets, NSGs with least-privilege rules
4. **Virtual Machines** &mdash; 3 VMs provisioned in parallel
5. **Database setup** &mdash; installs MySQL, creates user and schema (via SSH)
6. **Backend setup** &mdash; builds Spring PetClinic REST from source, runs as systemd service (via SSH)
7. **Frontend setup** &mdash; builds Angular app, configures Nginx reverse proxy (via SSH)
8. **Health checks** &mdash; each service is verified before proceeding to the next

## Tech Stack

| Layer          | Technology                              |
|----------------|-----------------------------------------|
| Infrastructure | Azure VMs, VNet, NSG, Azure CLI         |
| Automation     | Python 3.10+, Bash                      |
| Frontend       | Angular, Nginx                          |
| Backend        | Spring Boot (REST API), Java 17, Maven  |
| Database       | MySQL 8.0                               |

## Project Structure

```
PetClinicDeployment/
├── main.py                  # entry point - full deployment
├── cleanup.py               # tears down all Azure resources
├── config.yaml              # infrastructure & app configuration
├── core/
│   ├── azure.py             # Azure CLI wrapper with logging
│   ├── infrastructure.py    # resource provisioning & SSH execution
│   ├── config.py            # YAML config loader & validator
│   ├── context.py           # DeployContext (runtime settings)
│   └── utils.py             # terminal colors
└── scripts/
    ├── setup_db.sh           # MySQL installation & config
    ├── setup_backend.sh      # Spring Boot build & systemd setup
    └── setup_frontend.sh     # Angular build & Nginx config
```

## Quick Start

### Prerequisites

- Python 3.10+
- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) installed
- An active Azure subscription

### Deploy

```bash
az login
python3 main.py
```

With live output from all commands:

```bash
python3 main.py --verbose
```

### Clean up

```bash
python3 cleanup.py
```

## Network Security

Backend and database VMs have **no public IP addresses**. All SSH provisioning is done through the frontend VM as a jump host. NSG rules restrict traffic to:

| Rule             | Port | Source         | Subnet   |
|------------------|------|---------------|----------|
| HTTP             | 80   | Internet      | Frontend |
| SSH              | 22   | Internet      | Frontend |
| Spring Boot API  | 9966 | VirtualNetwork| Backend  |
| MySQL            | 3306 | VirtualNetwork| Backend  |
| SSH (internal)   | 22   | VirtualNetwork| Backend  |

## Configuration

All infrastructure parameters are defined in `config.yaml` &mdash; VM sizes, network addressing, subnet layout, NSG rules, and database credentials. No values are hardcoded in the Python source.

## Logs

Each deployment run creates a timestamped directory under `logs/` containing:
- `azure.log` &mdash; all Azure CLI command outputs
- `setup_db.log`, `setup_backend.log`, `setup_frontend.log` &mdash; SSH script outputs
