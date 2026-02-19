import subprocess
import sys
import time
from typing import Any

from core.azure import run_az_command
from core.context import DeployContext
from core.utils import BOLD, CYAN, GREEN, RED, RESET


def create_resource_group(config: dict[str, Any], ctx: DeployContext) -> None:
    print(f"{BOLD}--- CREATING RESOURCE GROUP ---{RESET}")
    run_az_command(["az", "group", "create", "--name", config["resource_group"], "--location", config["location"]], ctx)


def create_key_vault(config: dict[str, Any], ctx: DeployContext) -> None:
    print(f"\n{BOLD}--- CREATING KEY VAULT ---{RESET}")
    run_az_command([
        "az", "keyvault", "create",
        "--name", config["key_vault"]["name"],
        "-g", config["resource_group"],
        "-l", config["location"],
    ], ctx)


def assign_keyvault_role(config: dict[str, Any], ctx: DeployContext) -> None:
    print(f"\n{BOLD}--- ASSIGNING KEY VAULT ROLE ---{RESET}")
    oid = run_az_command(["az", "ad", "signed-in-user", "show", "--query", "id", "-o", "tsv"], ctx).strip()
    sub_id = run_az_command(["az", "account", "show", "--query", "id", "-o", "tsv"], ctx).strip()

    kv_name = config["key_vault"]["name"]
    rg = config["resource_group"]
    scope = f"/subscriptions/{sub_id}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/{kv_name}"

    run_az_command([
        "az", "role", "assignment", "create",
        "--role", "Key Vault Secrets Officer",
        "--assignee-object-id", oid,
        "--assignee-principal-type", "User",
        "--scope", scope,
    ], ctx)


def wait_for_keyvault_access(vault_name: str, max_wait: int = 180) -> None:
    """Polls Key Vault until RBAC role assignment propagates."""
    print(f"{CYAN}Waiting for RBAC propagation (up to {max_wait}s)...{RESET}")
    elapsed = 0
    while elapsed < max_wait:
        result = subprocess.run(
            ["az", "keyvault", "secret", "list", "--vault-name", vault_name, "--query", "[]", "-o", "tsv"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            print(f"{GREEN}[OK]{RESET} Key Vault access confirmed after {elapsed}s.")
            return
        time.sleep(15)
        elapsed += 15
        print(f"{CYAN}  Still waiting... ({elapsed}s){RESET}")
    print(f"{RED}[WARNING]{RESET} Propagation timeout — proceeding anyway.")


def store_secret(vault_name: str, name: str, value: str, ctx: DeployContext) -> None:
    print(f"{CYAN}Storing secret '{name}' in Key Vault '{vault_name}'...{RESET}")
    run_az_command([
        "az", "keyvault", "secret", "set",
        "--vault-name", vault_name,
        "--name", name, "--value", value,
    ], ctx)


def get_secret(vault_name: str, name: str, ctx: DeployContext) -> str:
    print(f"{CYAN}Retrieving secret '{name}' from Key Vault '{vault_name}'...{RESET}")
    return run_az_command([
        "az", "keyvault", "secret", "show",
        "--vault-name", vault_name,
        "--name", name,
        "--query", "value", "-o", "tsv",
    ], ctx).strip()


def create_network_stack(config: dict[str, Any], ctx: DeployContext) -> None:
    rg, loc, net = config["resource_group"], config["location"], config["network"]
    print(f"\n{BOLD}--- CREATING NETWORK STACK ---{RESET}")

    # fmt: off
    run_az_command([
        "az", "network", "vnet", "create",
        "-g", rg, "-l", loc, "-n", net["vnet_name"],
        "--address-prefix", net["vnet_address"]
    ], ctx)
    # fmt: on

    for _, sn_val in net["subnets"].items():
        nsg_name = sn_val["nsg_name"]
        print(f"{CYAN}Configuring NSG: {nsg_name}{RESET}")

        run_az_command(["az", "network", "nsg", "create", "-g", rg, "-l", loc, "-n", nsg_name], ctx)

        if "rules" in sn_val:
            for rule in sn_val["rules"]:
                # fmt: off
                run_az_command([
                    "az", "network", "nsg", "rule", "create",
                    "-g", rg, "--nsg-name", nsg_name,
                    "--name", rule["name"], "--priority", str(rule["priority"]),
                    "--destination-port-range", str(rule["port"]),
                    "--access", rule["access"], "--protocol", rule["protocol"],
                    "--direction", "Inbound",
                    "--source-address-prefix", rule.get("source", "VirtualNetwork"),
                    "--destination-address-prefix", "*", "--source-port-range", "*"
                ], ctx)
                # fmt: on

        # fmt: off
        run_az_command([
            "az", "network", "vnet", "subnet", "create",
            "-g", rg, "--vnet-name", net["vnet_name"],
            "-n", sn_val["name"], "--address-prefix", sn_val["address"],
            "--network-security-group", nsg_name
        ], ctx)
        # fmt: on


def create_vms(config: dict[str, Any]) -> None:
    print(f"\n{BOLD}--- CREATING VMS ---{RESET}")
    processes: dict[str, subprocess.Popen[str]] = {}

    for _, vm_data in config["compute"].items():
        sn_info = config["network"]["subnets"][vm_data["subnet"]]
        # fmt: off
        cmd = [
            "az", "vm", "create",
            "-g", config["resource_group"], "-l", config["location"],
            "-n", vm_data["name"], "--image", vm_data["image"],
            "--size", vm_data["size"], "--admin-username", vm_data["admin_username"],
            "--vnet-name", config["network"]["vnet_name"], "--subnet", sn_info["name"],
            "--nsg", "", "--generate-ssh-keys"
        ]
        # fmt: on

        if vm_data.get("public_ip"):
            cmd.extend(["--public-ip-address", vm_data["public_ip"]])
        else:
            cmd.extend(["--public-ip-address", ""])

        print(f"{CYAN}{BOLD}[STARTING]{RESET} {vm_data['name']}")
        processes[vm_data["name"]] = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    print(f"\n{CYAN}Waiting for all VMs to be created...{RESET}")
    for name, process in processes.items():
        _, stderr = process.communicate()
        if process.returncode != 0:
            print(f"{RED}{BOLD}[FAILED]{RESET} {name}: {stderr.strip()}")
            sys.exit(1)
        print(f"{GREEN}{BOLD}[SUCCESS]{RESET} {name} created.")

    print(f"{CYAN}{'-' * 45}{RESET}")


def get_deployment_report(config: dict[str, Any], ctx: DeployContext) -> dict[str, dict[str, str]]:
    print(f"\n{BOLD}--- GATHERING IP ADDRESSES ---{RESET}")
    report: dict[str, dict[str, str]] = {}
    for _, vm_val in config["compute"].items():
        name = vm_val["name"]
        report[name] = {}
        # fmt: off
        report[name]["private"] = run_az_command([
            "az", "vm", "list-ip-addresses", "-g", config["resource_group"], "-n", name,
            "--query", "[0].virtualMachine.network.privateIpAddresses[0]", "-o", "tsv"
        ], ctx).strip()
        if vm_val.get("public_ip"):
            report[name]["public"] = run_az_command([
                "az", "vm", "list-ip-addresses", "-g", config["resource_group"], "-n", name,
                "--query", "[0].virtualMachine.network.publicIpAddresses[0].ipAddress", "-o", "tsv"
            ], ctx).strip()
        # fmt: on
    return report


def provision_infrastructure(config: dict[str, Any], ctx: DeployContext) -> dict[str, dict[str, str]]:
    create_resource_group(config, ctx)

    kv_name = config["key_vault"]["name"]
    create_key_vault(config, ctx)
    assign_keyvault_role(config, ctx)
    wait_for_keyvault_access(kv_name)
    store_secret(kv_name, "db-password", config["database"]["password"], ctx)

    create_network_stack(config, ctx)
    create_vms(config)

    return get_deployment_report(config, ctx)
