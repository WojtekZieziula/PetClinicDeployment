import sys
from typing import Any

import yaml

from core.utils import RED, RESET


def load_configuration(path: str) -> dict[str, Any]:
    """Loads YAML configuration."""
    try:
        with open(path) as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        print(f"{RED}[ERROR]{RESET} Configuration file '{path}' not found!")
        sys.exit(1)


def _check_keys(data: dict[str, Any], keys: list[str], context: str) -> None:
    for key in keys:
        if key not in data:
            print(f"{RED}[ERROR]{RESET} Missing '{key}' in {context}")
            sys.exit(1)


def validate_config(config: dict[str, Any]) -> None:
    """Validates the configuration dictionary."""
    _check_keys(config, ["resource_group", "location", "network", "database", "compute"], "config.yaml")
    _check_keys(config["network"], ["vnet_name", "vnet_address", "subnets"], "config.yaml -> network")
    _check_keys(config["database"], ["user", "password"], "config.yaml -> database")

    subnet_names = set(config["network"]["subnets"].keys())

    vm_required = ["name", "size", "image", "admin_username", "subnet"]
    for vm_key, vm_data in config["compute"].items():
        ctx = f"config.yaml -> compute -> {vm_key}"
        _check_keys(vm_data, vm_required, ctx)

        if vm_data["subnet"] not in subnet_names:
            print(
                f"{RED}[ERROR]{RESET} VM '{vm_key}' references subnet '{vm_data['subnet']}' "
                f"which is not defined in network.subnets (available: {', '.join(subnet_names)})"
            )
            sys.exit(1)
