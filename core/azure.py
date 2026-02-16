import os
import subprocess
import sys

from core.context import DeployContext
from core.utils import BOLD, CYAN, GREEN, RED, RESET


def preflight_check() -> None:
    """Verifies that Azure CLI is installed and user is logged in."""
    try:
        subprocess.run(["az", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except FileNotFoundError:
        print(f"{RED}{BOLD}[ERROR]{RESET} Azure CLI (az) is not installed.")
        print("Install it: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli")
        sys.exit(1)

    result = subprocess.run(["az", "account", "show"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode != 0:
        print(f"{RED}{BOLD}[ERROR]{RESET} Not logged in to Azure. Run 'az login' first.")
        sys.exit(1)

    print(f"{GREEN}{BOLD}[OK]{RESET} Azure CLI authenticated.")


def run_az_command(command: list[str], ctx: DeployContext | None = None) -> str:
    """Executes Azure CLI commands and streams the output in real-time."""
    cmd_str: str = " ".join(command)
    print(f"{CYAN}{BOLD}[RUNNING]{RESET} {cmd_str}")

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)

    verbose = ctx.verbose if ctx else False
    log_dir = ctx.log_dir if ctx else "logs"
    log_path = os.path.join(log_dir, "azure.log")

    full_output: list[str] = []
    if process.stdout:
        os.makedirs(log_dir, exist_ok=True)
        with open(log_path, "a") as log_file:
            log_file.write(f"--- {cmd_str} ---\n")
            for line in process.stdout:
                clean_line = line.strip()
                if clean_line:
                    log_file.write(clean_line + "\n")
                    if verbose:
                        print(f"  {clean_line}")
                    full_output.append(clean_line)

    _, stderr = process.communicate()

    if process.returncode != 0:
        print(f"{RED}{BOLD}[PHASE FAILED]{RESET}")
        print(f"{RED}Error Details: {stderr.strip()}{RESET}")
        sys.exit(1)

    print(f"{GREEN}{BOLD}[SUCCESS]{RESET} Phase completed.")
    print(f"{CYAN}{'-' * 45}{RESET}")
    return "\n".join(full_output)
