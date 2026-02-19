import sys

from core.azure import run_az_command
from core.config import load_configuration
from core.utils import BOLD, RED, RESET, YELLOW


def main() -> None:
    config = load_configuration("config.yaml")
    rg_name: str = config["resource_group"]
    kv_name: str = config["key_vault"]["name"]

    print(f"{RED}{BOLD}--- AZURE RESOURCE CLEANUP ---{RESET}")
    print(f"{YELLOW}This will delete the entire Resource Group: {BOLD}{rg_name}{RESET}")

    confirm = input("\nAre you sure you want to proceed? (y/n): ")

    if confirm.lower() != "y":
        print(f"\n{BOLD}Cleanup aborted.{RESET}")
        sys.exit(0)

    print(f"\n{BOLD}Deleting resources...{RESET}")

    print(f"{BOLD}Soft-deleting Key Vault '{kv_name}'...{RESET}")
    run_az_command(["az", "keyvault", "delete", "--name", kv_name, "--resource-group", rg_name])

    run_az_command(["az", "group", "delete", "--name", rg_name, "--yes", "--no-wait"])

    print(f"{BOLD}Purging Key Vault '{kv_name}'...{RESET}")
    run_az_command(["az", "keyvault", "purge", "--name", kv_name, "--no-wait"])

    print(f"\n{RED}{BOLD}Resource Group '{rg_name}' has been scheduled for deletion.{RESET}")
    print(f"{RED}It may take a few minutes to fully disappear from the portal.{RESET}")


if __name__ == "__main__":
    main()
