"""Runtime server type definitions."""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class RuntimeConfig:
    """Configuration for runtime environments."""
    github_url: str


@dataclass
class Environment:
    """Complete runtime environment."""
    id: str
    config: RuntimeConfig
    created_at: datetime
    root_dir: Path
    bin_dir: Path
    work_dir: Path
    tmp_dir: Path
    env_vars: Dict[str, str]
