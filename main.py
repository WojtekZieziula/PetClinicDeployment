import argparse
import os
from datetime import datetime

from core.azure import preflight_check
from core.config import load_configuration, validate_config
from core.context import DeployContext
from core.deploy import deploy_application, verify_deployment
from core.infrastructure import provision_infrastructure
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

    ips = provision_infrastructure(config, ctx)
    deploy_application(config, ips, ctx)

    print(f"\n{BOLD}{'=' * 50}{RESET}")
    print(f"{GREEN}{BOLD}DEPLOYMENT SUCCESSFUL!{RESET}")

    public_ip = ips[config["compute"]["frontend_vm"]["name"]].get("public")
    frontend_port = str(config["compute"]["frontend_vm"]["port"])

    if public_ip:
        print(f"{BOLD}Link:{RESET} http://{public_ip}/petclinic/")

    print(f"{BOLD}Logs:{RESET} {log_dir}/")
    print(f"{BOLD}{'=' * 50}{RESET}\n")

    if public_ip:
        verify_deployment(public_ip, frontend_port)


if __name__ == "__main__":
    main()
