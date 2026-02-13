import yaml
import sys
import subprocess
from typing import Dict, Any, List
from utils import GREEN, RED, YELLOW, CYAN, RESET, BOLD


def load_configuration(path: str) -> Dict[str, Any]:
    """
    Loads YAML configuration.
    Returns a dictionary with string keys and values of any type.
    """
    try:
        with open(path, "r") as file:
            config: Dict[str, Any] = yaml.safe_load(file)
            return config
    except FileNotFoundError:
        print(f"{RED}[ERROR]{RESET} Configuration file '{path}' not found!")
        sys.exit(1)


def validate_config(config: Dict[str, Any]) -> None:
    """
    Validates the configuration dictionary.
    Returns None, as it either passes or exits the script.
    """
    required_keys: List[str] = ['resource_group', 'location']
    for key in required_keys:
        if key not in config:
            print(f"{RED}[ERROR]{RESET} Missing required key '{key}' in config.yaml")
            sys.exit(1)


def run_az_command(command: List[str]) -> str:
    """
    Executes Azure CLI commands and returns the output as a string.
    """
    cmd_str: str = ' '.join(command)

    print(f"{CYAN}{BOLD}[RUNNING]{RESET} {cmd_str}")

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"{RED}{BOLD}[PHASE FAILED]{RESET}")
        print(f"{RED}Error Details: {result.stderr.strip()}{RESET}")
        sys.exit(1)

    if result.stdout:
        print(f"{GREEN}{BOLD}[SUCCESS]{RESET} Azure response received.")
        print(result.stdout.strip())
        print(f"{CYAN}{'-' * 40}{RESET}")

    return result.stdout


def main() -> None:
    config: Dict[str, Any] = load_configuration("config.yaml")
    validate_config(config)

    print(f"{BOLD}--- CREATING RESOURCE GROUP ---{RESET}\n")

    run_az_command([
        "az", "group", "create",
        "--name", config['resource_group'],
        "--location", config['location']
    ])

if __name__ == "__main__":
    main()