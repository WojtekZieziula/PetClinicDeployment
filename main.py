import argparse
import os
from datetime import datetime

from core.azure import preflight_check
from core.config import load_configuration, validate_config
from core.context import DeployContext
from core.infrastructure import (
    create_network_stack,
    create_resource_group,
    create_vms,
    get_deployment_report,
    run_ssh_script,
    wait_for_ssh,
)
from core.utils import BOLD, GREEN, RESET


def main() -> None:
    parser = argparse.ArgumentParser(description="PetClinic Azure Deployment Tool")
    parser.add_argument(
        "--verbose", action="store_true", help="Show live output from SSH scripts and Azure CLI on terminal"
    )
    args = parser.parse_args()

    preflight_check()

    config = load_configuration("config.yaml")
    validate_config(config)

    log_dir = os.path.join("logs", datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    os.makedirs(log_dir)

    ctx = DeployContext(verbose=args.verbose, log_dir=log_dir)

    print(f"{BOLD}=== PET CLINIC DEPLOYMENT ==={RESET}\n")

    create_resource_group(config, ctx)
    create_network_stack(config, ctx)
    create_vms(config)

    ips = get_deployment_report(config, ctx)

    db_vm_name = config["compute"]["db_vm"]["name"]
    backend_vm_name = config["compute"]["backend_vm"]["name"]
    frontend_vm_name = config["compute"]["frontend_vm"]["name"]

    db_private_ip = ips[db_vm_name]["private"]
    backend_private_ip = ips[backend_vm_name]["private"]
    frontend_public_ip = ips[frontend_vm_name]["public"]
    admin = config["compute"]["frontend_vm"]["admin_username"]

    db_user = config["database"]["user"]
    db_pass = config["database"]["password"]

    db_port = str(config["database"]["port"])
    backend_port = str(config["compute"]["backend_vm"]["port"])
    frontend_port = str(config["compute"]["frontend_vm"]["port"])

    wait_for_ssh(frontend_public_ip)

    run_ssh_script(
        "scripts/setup_db.sh",
        db_private_ip,
        admin,
        ctx,
        params=[db_port, db_user, db_pass],
        jump_host=frontend_public_ip,
    )
    run_ssh_script(
        "scripts/setup_backend.sh",
        backend_private_ip,
        admin,
        ctx,
        params=[db_private_ip, db_port, backend_port, db_user, db_pass],
        jump_host=frontend_public_ip,
    )
    run_ssh_script(
        "scripts/setup_frontend.sh", frontend_public_ip, admin, ctx, params=[backend_private_ip, backend_port, frontend_port]
    )

    print(f"\n{BOLD}{'=' * 50}{RESET}")
    print(f"{GREEN}{BOLD}DEPLOYMENT SUCCESSFUL!{RESET}")

    public_ip = ips[frontend_vm_name].get("public")
    if public_ip:
        print(f"{BOLD}Link:{RESET} http://{public_ip}/petclinic/")

    print(f"{BOLD}Logs:{RESET} {log_dir}/")
    print(f"{BOLD}{'=' * 50}{RESET}\n")


if __name__ == "__main__":
    main()
