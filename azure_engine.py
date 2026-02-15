import os
import subprocess
import sys
from typing import List
from utils import GREEN, RED, CYAN, RESET, BOLD

_VERBOSE: bool = False
_LOG_DIR: str = "logs"

def set_logging_level(verbose: bool, log_dir: str) -> None:
    """Sets the global verbosity and log directory for Azure CLI output."""
    global _VERBOSE, _LOG_DIR
    _VERBOSE = verbose
    _LOG_DIR = log_dir

def run_az_command(command: List[str]) -> str:
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

    log_path = os.path.join(_LOG_DIR, "azure.log")

    full_output: List[str] = []
    if process.stdout:
        with open(log_path, "a") as log_file:
            log_file.write(f"--- {cmd_str} ---\n")
            for line in process.stdout:
                clean_line = line.strip()
                if clean_line:
                    log_file.write(clean_line + "\n")
                    if _VERBOSE:
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
