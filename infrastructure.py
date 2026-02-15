import json
from typing import Dict, List, Any
from azure_engine import run_az_command
from utils import BOLD, RESET, CYAN, GREEN, RED


def create_resource_group(config: Dict[str, Any]) -> None:
    print(f"{BOLD}--- CREATING RESOURCE GROUP ---{RESET}")
    run_az_command([
        "az", "group", "create",
        "--name", config['resource_group'],
        "--location", config['location']
    ])


def create_network_stack(config: Dict[str, Any]) -> None:
    rg, loc, net = config['resource_group'], config['location'], config['network']
    print(f"\n{BOLD}--- CREATING NETWORK STACK ---{RESET}")

    run_az_command(["az", "network", "vnet", "create", "-g", rg, "-l", loc, "-n", net['vnet_name'], "--address-prefix", net['vnet_address']])

    for sn_key, sn_val in net['subnets'].items():
        nsg_name = sn_val['nsg_name']
        print(f"{CYAN}Configuring NSG: {nsg_name}{RESET}")

        run_az_command(["az", "network", "nsg", "create", "-g", rg, "-l", loc, "-n", nsg_name])

        if 'rules' in sn_val:
            for rule in sn_val['rules']:
                run_az_command([
                    "az", "network", "nsg", "rule", "create", "-g", rg, "--nsg-name", nsg_name,
                    "--name", rule['name'], "--priority", str(rule['priority']),
                    "--destination-port-range", str(rule['port']), "--access", rule['access'],
                    "--protocol", rule['protocol'], "--direction", "Inbound",
                    "--source-address-prefix", rule.get('source', 'VirtualNetwork'),
                    "--destination-address-prefix", "*", "--source-port-range", "*"
                ])

        run_az_command([
            "az", "network", "vnet", "subnet", "create", "-g", rg, "--vnet-name", net['vnet_name'],
            "-n", sn_val['name'], "--address-prefix", sn_val['address'],
            "--network-security-group", nsg_name
        ])

def create_vms(config: Dict[str, Any]) -> None:
    print(f"\n{BOLD}--- CREATING VMS ---{RESET}")
    for vm_key, vm_data in config['compute'].items():
        sn_info = config['network']['subnets'][vm_data['subnet']]
        cmd = [
            "az", "vm", "create",
            "-g", config['resource_group'],
            "-l", config['location'],
            "-n", vm_data['name'],
            "--image", vm_data['image'],
            "--size", vm_data['size'],
            "--admin-username", vm_data['admin_username'],
            "--vnet-name", config['network']['vnet_name'],
            "--subnet", sn_info['name'],
            "--nsg", "",
            "--generate-ssh-keys"
        ]

        if vm_data.get('public_ip'):
            cmd.extend(["--public-ip-address", vm_data['public_ip']])
        else:
            cmd.extend(["--public-ip-address", ""])

        run_az_command(cmd)

def get_deployment_report(config: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    print(f"\n{BOLD}--- GATHERING IP ADDRESSES ---{RESET}")
    report = {}
    for vm_key, vm_val in config['compute'].items():
        name = vm_val['name']
        report[name] = {}
        report[name]['private'] = run_az_command(["az", "vm", "list-ip-addresses", "-g", config['resource_group'], "-n", name, "--query", "[0].virtualMachine.network.privateIpAddresses[0]", "-o", "tsv"]).strip()
        if vm_val.get('public_ip'):
            report[name]['public'] = run_az_command(["az", "vm", "list-ip-addresses", "-g", config['resource_group'], "-n", name, "--query", "[0].virtualMachine.network.publicIpAddresses[0].ipAddress", "-o", "tsv"]).strip()
    return report

def run_config_script(config: Dict[str, Any], vm_name: str, script_path: str, params: List[str] = None) -> None:
    print(f"\n{CYAN}{BOLD}Executing {script_path} on {vm_name}...{RESET}")
    cmd = ["az", "vm", "run-command", "invoke", "-g", config['resource_group'], "-n", vm_name, "--command-id", "RunShellScript", "--scripts", f"@{script_path}"]
    if params: cmd.extend(["--parameters"] + params)
    raw_output = run_az_command(cmd)
    try:
        logs = json.loads(raw_output).get('value', [{}])[0].get('message', 'No logs found.')
        print(f"\n{GREEN}{BOLD}--- BASH LOGS FROM {vm_name} ---{RESET}\n{logs}\n{GREEN}{BOLD}--- END ---{RESET}")
    except: print(f"{RED}Failed to parse logs for {vm_name}{RESET}")
