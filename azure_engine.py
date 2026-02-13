import subprocess
import sys
from typing import List
from utils import GREEN, RED, CYAN, RESET, BOLD


def run_az_command(command: List[str], show_json: bool = False) -> str:
    """
    Executes Azure CLI commands and streams the output in real-time.
    """
    cmd_str: str = ' '.join(command)
    print(f"{CYAN}{BOLD}[RUNNING]{RESET} {cmd_str}")

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    full_output: List[str] = []
    if process.stdout:
        for line in process.stdout:
            clean_line = line.strip()
            if clean_line:
                if show_json:
                    print(f"  {clean_line}")
                full_output.append(clean_line)

    stdout_rem, stderr = process.communicate()

    if process.returncode != 0:
        print(f"{RED}{BOLD}[PHASE FAILED]{RESET}")
        print(f"{RED}Error Details: {stderr.strip()}{RESET}")
        sys.exit(1)

    print(f"{GREEN}{BOLD}[SUCCESS]{RESET} Phase completed.")
    print(f"{CYAN}{'-' * 45}{RESET}")
    return "\n".join(full_output)

