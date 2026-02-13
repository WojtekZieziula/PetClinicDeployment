from typing import Dict, Any
from azure_engine import run_az_command
from utils import BOLD, RESET, CYAN, GREEN


def provision_resource_group(config: Dict[str, Any], show_json: bool) -> None:
    """
    Creates Resource Group
    """
    print(f"{BOLD}--- CREATING RESOURCE GROUP ---{RESET}")
    run_az_command([
        "az", "group", "create",
        "--name", config['resource_group'],
        "--location", config['location']
    ], show_json)


def provision_network(config: Dict[str, Any], show_json: bool) -> None:
    """
    Creates Virtual Network and Subnets.
    Implements separation of public and private components.
    """
    rg: str = config['resource_group']
    net: Dict[str, Any] = config['network']

    print(f"\n{BOLD}--- CREATING NETWORK INFRASTRUCTURE ---{RESET}")

    run_az_command([
        "az", "network", "vnet", "create",
        "--resource-group", rg,
        "--name", net['vnet_name'],
        "--address-prefix", net['vnet_address']
    ], show_json)

    for sn_key in net['subnets']:
        sn = net['subnets'][sn_key]
        print(f"{CYAN}Adding Subnet: {sn['name']}{RESET}")
        run_az_command([
            "az", "network", "vnet", "subnet", "create",
            "--resource-group", rg,
            "--vnet-name", net['vnet_name'],
            "--name", sn['name'],
            "--address-prefixes", sn['address']
        ], show_json)