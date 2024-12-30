"""Type definitions."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Any
import tempfile


class RuntimeManager(str, Enum):
    """Runtime manager types."""

    NPX = "npx"
    BUN = "bunx"
    UVX = "uv"
    PIPX = "pipx"


@dataclass
class EnvironmentConfig:
    """Runtime environment configuration."""

    github_url: str


@dataclass
class Environment:
    """Runtime environment instance."""

    id: str
    config: EnvironmentConfig
    created_at: datetime
    root_dir: Path
    bin_dir: Path
    tmp_dir: Path
    work_dir: Path
    manager: Optional[RuntimeManager]
    env_vars: Dict[str, str]
    _temp_dir: Optional[tempfile.TemporaryDirectory] = None


@dataclass  
class Runtime:
    """Runtime detection result."""

    manager: RuntimeManager
    env_vars: Dict[str, Any]