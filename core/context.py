from dataclasses import dataclass


@dataclass
class DeployContext:
    verbose: bool
    log_dir: str
