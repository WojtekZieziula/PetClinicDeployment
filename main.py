import argparse
from config_manager import load_configuration, validate_config
from infrastructure import (
    create_resource_group,
    create_network_stack,
    create_vms,
    get_deployment_report,
    wait_for_ssh,
    run_ssh_script
)
from azure_engine import set_logging_level
from utils import GREEN, BOLD, RESET

def main() -> None:
    parser = argparse.ArgumentParser(description="PetClinic Azure Deployment Tool")
    parser.add_argument('--verbose', action='store_true', help="Show live output from SSH scripts and Azure CLI on terminal")
    args = parser.parse_args()

    set_logging_level(args.verbose)

    config = load_configuration("config.yaml")
    validate_config(config)

    print(f"{BOLD}=== PET CLINIC DEPLOYMENT ==={RESET}\n")

    create_resource_group(config)
    create_network_stack(config)
    create_vms(config)

    ips = get_deployment_report(config)

    db_vm_name = config['compute']['db_vm']['name']
    backend_vm_name = config['compute']['backend_vm']['name']
    frontend_vm_name = config['compute']['frontend_vm']['name']

    db_private_ip = ips[db_vm_name]['private']
    backend_private_ip = ips[backend_vm_name]['private']
    frontend_public_ip = ips[frontend_vm_name]['public']
    admin = config['compute']['frontend_vm']['admin_username']

    wait_for_ssh(frontend_public_ip)

    run_ssh_script("scripts/setup_db.sh", db_private_ip, admin, ["3306"], jump_host=frontend_public_ip, verbose=args.verbose)
    run_ssh_script("scripts/setup_backend.sh", backend_private_ip, admin, [db_private_ip, "3306", "9966"], jump_host=frontend_public_ip, verbose=args.verbose)
    run_ssh_script("scripts/setup_frontend.sh", frontend_public_ip, admin, [backend_private_ip, "9966", "80"], verbose=args.verbose)

    print(f"\n{BOLD}{'='*50}{RESET}")
    print(f"{GREEN}{BOLD}DEPLOYMENT SUCCESSFUL!{RESET}")

    public_ip = ips[frontend_vm_name].get('public')
    if public_ip:
        print(f"{BOLD}Link:{RESET} http://{public_ip}/petclinic/")

    print(f"{BOLD}Logs:{RESET} logs/")
    print(f"{BOLD}{'='*50}{RESET}\n")

if __name__ == "__main__":
    main()
