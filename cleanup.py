import sys
from config_manager import load_configuration
from azure_engine import run_az_command
from utils import RED, YELLOW, BOLD, RESET

def main() -> None:
    config = load_configuration("config.yaml")
    rg_name: str = config['resource_group']

    print(f"{RED}{BOLD}--- AZURE RESOURCE CLEANUP ---{RESET}")
    print(f"{YELLOW}This will delete the entire Resource Group: {BOLD}{rg_name}{RESET}")

    confirm = input(f"\nAre you sure you want to proceed? (y/n): ")

    if confirm.lower() != 'y':
        print(f"\n{BOLD}Cleanup aborted.{RESET}")
        sys.exit(0)

    print(f"\n{BOLD}Deleting resources...{RESET}")

    run_az_command([
        "az", "group", "delete",
        "--name", rg_name,
        "--yes", "--no-wait"
    ])

    print(f"\n{RED}{BOLD}Resource Group '{rg_name}' has been scheduled for deletion.{RESET}")
    print(f"{RED}It may take a few minutes to fully disappear from the portal.{RESET}")

if __name__ == "__main__":
    main()
