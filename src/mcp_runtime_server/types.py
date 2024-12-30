"""Runtime server type definitions."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict


class RuntimeManager(str, Enum):
    """Runtime manager types."""
    NPX = "npx"
    BUN = "bun"
    UVX = "uvx"
    PIPX = "pipx"


@dataclass(frozen=True)
class RuntimeConfig:
    """Configuration for runtime environments."""
    github_url: str
    manager: RuntimeManager


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