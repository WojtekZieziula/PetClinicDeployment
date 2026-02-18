import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any

from core.context import DeployContext
from core.infrastructure import get_secret
from core.utils import BOLD, CYAN, GREEN, RED, RESET


def wait_for_ssh(host: str, timeout: int = 300, interval: int = 5) -> None:
    print(f"\n{CYAN}Waiting for SSH on {host}...{RESET}")
    start = time.time()
    while time.time() - start < timeout:
        try:
            sock = socket.create_connection((host, 22), timeout=5)
            sock.close()
            print(f"{GREEN}SSH ready on {host}{RESET}")
            return
        except (TimeoutError, ConnectionRefusedError, OSError):
            time.sleep(interval)
    print(f"{RED}SSH timeout after {timeout}s for {host}{RESET}")
    sys.exit(1)


def run_ssh_script(
    script_path: str,
    target_host: str,
    user: str,
    ctx: DeployContext,
    params: list[str] | None = None,
    jump_host: str | None = None,
) -> None:
    print(f"\n{CYAN}{BOLD}Executing {script_path} on {user}@{target_host}...{RESET}")

    ssh_flags = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
    ssh_cmd = ["ssh", *ssh_flags]

    if jump_host:
        ssh_cmd += ["-J", f"{user}@{jump_host}"]

    ssh_cmd.append(f"{user}@{target_host}")

    remote_cmd = "bash -s"
    if params:
        remote_cmd += " " + " ".join(params)
    ssh_cmd.append(remote_cmd)

    with open(script_path) as f:
        script_content = f.read()

    log_filename = os.path.basename(script_path).replace(".sh", ".log")
    log_path = os.path.join(ctx.log_dir, log_filename)

    process = subprocess.Popen(
        ssh_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    process.stdin.write(script_content)
    process.stdin.close()

    with open(log_path, "w") as log_file:
        for line in process.stdout:
            log_file.write(line)
            if ctx.verbose:
                print(line, end="")

    process.wait()
    if process.returncode != 0:
        print(f"{RED}{BOLD}Script {script_path} failed on {target_host} (exit code {process.returncode}){RESET}")
        print(f"Logs saved to {log_path}")
        sys.exit(1)

    print(f"{GREEN}{BOLD}Script {script_path} completed on {target_host}{RESET}")
    print(f"Logs saved to {log_path}")


def verify_deployment(public_ip: str, frontend_port: str) -> None:
    print(f"\n{BOLD}--- END-TO-END VERIFICATION ---{RESET}")

    base_url = f"http://{public_ip}:{frontend_port}" if frontend_port != "80" else f"http://{public_ip}"
    endpoints = [
        (f"{base_url}/petclinic/", "Frontend"),
        (f"{base_url}/petclinic/api/pettypes", "Full stack (Frontend -> Backend -> DB)"),
    ]

    for url, label in endpoints:
        success = False
        print(f"{CYAN}Testing {label}: {url}{RESET}")
        for attempt in range(1, 11):
            try:
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        print(f"  {GREEN}{BOLD}[PASS]{RESET} {label} returned HTTP 200 (attempt {attempt})")
                        success = True
                        break
            except (urllib.error.URLError, urllib.error.HTTPError, OSError):
                pass
            time.sleep(3)

        if not success:
            print(f"  {RED}{BOLD}[WARN]{RESET} {label} did not return HTTP 200 after 10 attempts")
            print(f"  {RED}URL: {url}{RESET}")


def deploy_application(config: dict[str, Any], ips: dict[str, dict[str, str]], ctx: DeployContext) -> None:
    db_private_ip = ips[config["compute"]["db_vm"]["name"]]["private"]
    backend_private_ip = ips[config["compute"]["backend_vm"]["name"]]["private"]
    frontend_public_ip = ips[config["compute"]["frontend_vm"]["name"]]["public"]
    admin = config["compute"]["frontend_vm"]["admin_username"]

    kv_name = config["key_vault"]["name"]
    db_name = config["database"]["name"]
    db_user = config["database"]["user"]
    db_pass = get_secret(kv_name, "db-password", ctx)

    db_port = str(config["database"]["port"])
    backend_port = str(config["compute"]["backend_vm"]["port"])
    frontend_port = str(config["compute"]["frontend_vm"]["port"])

    wait_for_ssh(frontend_public_ip)

    run_ssh_script(
        "scripts/setup_db.sh",
        db_private_ip,
        admin,
        ctx,
        params=[db_port, db_user, db_pass, db_name],
        jump_host=frontend_public_ip,
    )
    run_ssh_script(
        "scripts/setup_backend.sh",
        backend_private_ip,
        admin,
        ctx,
        params=[db_private_ip, db_port, backend_port, db_user, db_pass, db_name],
        jump_host=frontend_public_ip,
    )
    run_ssh_script(
        "scripts/setup_frontend.sh", frontend_public_ip, admin, ctx, params=[backend_private_ip, backend_port, frontend_port]
    )
