import os
import socket
import subprocess
import sys
import time
from typing import Dict, List, Any, Optional
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
    processes: Dict[str, subprocess.Popen] = {}

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

        print(f"{CYAN}{BOLD}[STARTING]{RESET} {vm_data['name']}")
        processes[vm_data['name']] = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    print(f"\n{CYAN}Waiting for all VMs to be created...{RESET}")
    for name, process in processes.items():
        _, stderr = process.communicate()
        if process.returncode != 0:
            print(f"{RED}{BOLD}[FAILED]{RESET} {name}: {stderr.strip()}")
            sys.exit(1)
        print(f"{GREEN}{BOLD}[SUCCESS]{RESET} {name} created.")

    print(f"{CYAN}{'-' * 45}{RESET}")

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

def wait_for_ssh(host: str, timeout: int = 300, interval: int = 5) -> None:
    print(f"\n{CYAN}Waiting for SSH on {host}...{RESET}")
    start = time.time()
    while time.time() - start < timeout:
        try:
            sock = socket.create_connection((host, 22), timeout=5)
            sock.close()
            print(f"{GREEN}SSH ready on {host}{RESET}")
            return
        except (socket.timeout, ConnectionRefusedError, OSError):
            time.sleep(interval)
    print(f"{RED}SSH timeout after {timeout}s for {host}{RESET}")
    sys.exit(1)


def run_ssh_script(script_path: str, target_host: str, user: str, params: Optional[List[str]] = None, jump_host: Optional[str] = None, verbose: bool = False, log_dir: str = "logs") -> None:
    print(f"\n{CYAN}{BOLD}Executing {script_path} on {user}@{target_host}...{RESET}")

    ssh_flags = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
    ssh_cmd = ["ssh"] + ssh_flags

    if jump_host:
        ssh_cmd += ["-J", f"{user}@{jump_host}"]

    ssh_cmd.append(f"{user}@{target_host}")

    remote_cmd = "bash -s"
    if params:
        remote_cmd += " " + " ".join(params)
    ssh_cmd.append(remote_cmd)

    with open(script_path, "r") as f:
        script_content = f.read()

    log_filename = os.path.basename(script_path).replace(".sh", ".log")
    log_path = os.path.join(log_dir, log_filename)

    process = subprocess.Popen(ssh_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    process.stdin.write(script_content)
    process.stdin.close()

    with open(log_path, "w") as log_file:
        for line in process.stdout:
            log_file.write(line)
            if verbose:
                print(line, end="")

    process.wait()
    if process.returncode != 0:
        print(f"{RED}{BOLD}Script {script_path} failed on {target_host} (exit code {process.returncode}){RESET}")
        print(f"Logs saved to {log_path}")
        sys.exit(1)

    print(f"{GREEN}{BOLD}Script {script_path} completed on {target_host}{RESET}")
    print(f"Logs saved to {log_path}")
