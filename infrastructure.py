from typing import Dict, Any
from azure_engine import run_az_command
from utils import BOLD, RESET, CYAN, GREEN


def provision_resource_group(config: Dict[str, Any]) -> None:
    """
    Creates Resource Group
    """
    print(f"{BOLD}--- CREATING RESOURCE GROUP ---{RESET}")
    run_az_command([
        "az", "group", "create",
        "--name", config['resource_group'],
        "--location", config['location']
    ])


def provision_network(config: Dict[str, Any]) -> None:
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
    ])

    for sn_key in net['subnets']:
        sn = net['subnets'][sn_key]
        print(f"{CYAN}Adding Subnet: {sn['name']}{RESET}")
        run_az_command([
            "az", "network", "vnet", "subnet", "create",
            "--resource-group", rg,
            "--vnet-name", net['vnet_name'],
            "--name", sn['name'],
            "--address-prefixes", sn['address']
        ])


def provision_nsgs(config: Dict[str, Any]) -> None:
    rg: str = config['resource_group']
    net: Dict[str, Any] = config['network']
    vnet_name: str = net['vnet_name']

    print(f"\n{BOLD}--- CREATING NETWORK SECURITY GROUPS ---{RESET}")

    for sn_key, sn_val in net['subnets'].items():
        nsg_name = sn_val['nsg_name']
        print(f"{CYAN}Creating NSG: {nsg_name} for {sn_val['name']}{RESET}")

        run_az_command([
            "az", "network", "nsg", "create",
            "--resource-group", rg,
            "--name", nsg_name
        ])

        if 'rules' in sn_val:
            for rule in sn_val['rules']:
                print(f"{CYAN}Adding rule: {rule['name']} (Port: {rule['port']}){RESET}")
                run_az_command([
                    "az", "network", "nsg", "rule", "create",
                    "--resource-group", rg,
                    "--nsg-name", nsg_name,
                    "--name", rule['name'],
                    "--priority", str(rule['priority']),
                    "--destination-port-ranges", str(rule['port']),
                    "--access", rule['access'],
                    "--protocol", rule['protocol'],
                    "--direction", "Inbound"
                ])

        print(f"{CYAN}Linking {nsg_name} to subnet {sn_val['name']}...{RESET}")
        run_az_command([
            "az", "network", "vnet", "subnet", "update",
            "--resource-group", rg,
            "--vnet-name", vnet_name,
            "--name", sn_val['name'],
            "--network-security-group", nsg_name
        ])

    print(f"{GREEN}{BOLD}All NSGs provisioned and linked.{RESET}")