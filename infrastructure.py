from typing import Dict, Any
from azure_engine import run_az_command
from utils import BOLD, RESET, CYAN, GREEN


def create_resource_group(config: Dict[str, Any]) -> None:
    print(f"{BOLD}--- CREATING RESOURCE GROUP ---{RESET}")
    run_az_command([
        "az", "group", "create",
        "--name", config['resource_group'],
        "--location", config['location']
    ])


def create_network_stack(config: Dict[str, Any]) -> None:
    rg = config['resource_group']
    loc = config['location']
    net = config['network']

    print(f"\n{BOLD}--- CREATING NETWORK STACK ---{RESET}")

    run_az_command([
        "az", "network", "vnet", "create",
        "--resource-group", rg, "--location", loc,
        "--name", net['vnet_name'], "--address-prefix", net['vnet_address']
    ])

    for sn_key, sn_val in net['subnets'].items():
        nsg_name = sn_val['nsg_name']
        print(f"{CYAN}Processing subnet stack: {sn_val['name']}{RESET}")

        run_az_command(["az", "network", "nsg", "create", "--resource-group", rg, "--location", loc, "--name", nsg_name])

        if 'rules' in sn_val:
            for rule in sn_val['rules']:
                run_az_command([
                    "az", "network", "nsg", "rule", "create",
                    "--resource-group", rg, "--nsg-name", nsg_name,
                    "--name", rule['name'], "--priority", str(rule['priority']),
                    "--destination-port-ranges", str(rule['port']),
                    "--access", rule['access'], "--protocol", rule['protocol']
                ])

        run_az_command([
            "az", "network", "vnet", "subnet", "create",
            "--resource-group", rg, "--vnet-name", net['vnet_name'],
            "--name", sn_val['name'], "--address-prefixes", sn_val['address'],
            "--network-security-group", nsg_name
        ])


def create_vms(config: Dict[str, Any]) -> None:
    print(f"\n{BOLD}--- CREATING VMS ---{RESET}")

    for vm_key, vm_data in config['compute'].items():
        sn_info = config['network']['subnets'][vm_data['subnet']]

        print(f"{CYAN}Deploying VM: {vm_data['name']} into {sn_info['name']}...{RESET}")

        _create_vm_template(vm_data, sn_info, config)


def _create_vm_template(vm_data: Dict[str, Any], sn_info: Dict[str, Any], config: Dict[str, Any]) -> None:
    run_az_command([
        "az", "vm", "create",
        "--resource-group", config['resource_group'],
        "--location", config['location'],
        "--name", vm_data['name'],
        "--image", vm_data['image'],
        "--size", vm_data['size'],
        "--admin-username", vm_data['admin_username'],
        "--vnet-name", config['network']['vnet_name'],
        "--subnet", sn_info['name'],
        "--public-ip-address", vm_data.get('public_ip', ""),
        "--generate-ssh-keys"
    ])
