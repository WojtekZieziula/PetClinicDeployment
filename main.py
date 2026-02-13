import argparse
from config_manager import load_configuration, validate_config
from infrastructure import provision_resource_group, provision_network, provision_nsgs
from azure_engine import set_logging_level
from utils import BOLD, RESET

def main() -> None:
    parser = argparse.ArgumentParser(description="PetClinic Azure Deployment Tool")
    parser.add_argument('--show-json', action='store_true', help="Show raw JSON response from Azure CLI")
    args = parser.parse_args()

    set_logging_level(args.show_json)

    config = load_configuration("config.yaml")
    validate_config(config)

    print(f"{BOLD}=== PET CLINIC DEPLOYMENT ==={RESET}\n")

    provision_resource_group(config)
    provision_network(config)
    provision_nsgs(config)

    print(f"\n{BOLD}=== DEPLOYMENT COMPLETED SUCCESSFULLY ==={RESET}")

if __name__ == "__main__":
    main()