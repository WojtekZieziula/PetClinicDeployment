import yaml
import sys
from typing import Dict, Any, List
from utils import RED, RESET


def load_configuration(path: str) -> Dict[str, Any]:
    """
    Loads YAML configuration.
    Returns a dictionary with string keys and values of any type.
    """
    try:
        with open(path, "r") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        print(f"{RED}[ERROR]{RESET} Configuration file '{path}' not found!")
        sys.exit(1)


def validate_config(config: Dict[str, Any]) -> None:
    """
    Validates the configuration dictionary.
    Returns None, as it either passes or exits the script.
    """
    required_keys: List[str] = ['resource_group', 'location', 'network']
    for key in required_keys:
        if key not in config:
            print(f"{RED}[ERROR]{RESET} Missing required key '{key}' in config.yaml")
            sys.exit(1)

    if 'vnet_address' not in config['network'] or 'subnets' not in config['network']:
        print(f"{RED}[ERROR]{RESET} Missing network details in config.yaml")
        sys.exit(1)
