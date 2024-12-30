"""Runtime server type definitions."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, EnumMeta
from pathlib import Path
from typing import Dict, Optional


class RuntimeManager(str, Enum):
    """Runtime manager types."""
    NPX = "npx"
    BUN = "bun"
    UVX = "uvx"
    PIPX = "pipx"


@dataclass(frozen=True)
class EnvironmentConfig:
    """Configuration for runtime environments."""
    github_url: str


@dataclass
class Environment:
    """Complete runtime environment."""
    id: str
    config: EnvironmentConfig
    created_at: datetime
    root_dir: Path
    bin_dir: Path
    work_dir: Path
    tmp_dir: Path
    manager: Optional[RuntimeManager]
    env_vars: Dict[str, str]