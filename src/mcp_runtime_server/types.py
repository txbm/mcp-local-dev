"""Type definitions."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, List
import tempfile


class Runtimes(str, Enum):
    PYTHON = "uv"
    NODE = "npm"
    BUN = "bun"

@dataclass(frozen=True)
class RuntimeSignature:
    config_files: List[str]
    env_vars: Dict[str, str]
    bin_path: str


class RuntimeManager(str, Enum):
    """Runtime manager types."""
    NODE = "node"
    BUN = "bun"
    UV = "uv"


@dataclass
class EnvironmentConfig:
    """Runtime environment configuration."""
    github_url: str

@dataclass(frozen=True)
class Environment:
    id: str
    config: EnvironmentConfig
    runtime: Runtimes
    work_dir: Path
    created_at: datetime
    sandbox_root: Path
    root_dir: Path
    bin_dir: Path
    env_vars: Dict[str, str]
    _temp_dir: Optional[tempfile.TemporaryDirectory] = None

@dataclass
class Runtime:
    """Runtime detection result."""
    manager: RuntimeManager
    env_vars: Dict[str, str]
