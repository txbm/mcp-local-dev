"""Runtime server type definitions."""
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


RuntimeManager = Enum('RuntimeManager', [
    ('NODE', 'node'),
    ('BUN', 'bun'),
    ('UV', 'uv')
])


@dataclass(frozen=True)
class RuntimeConfig:
    """Configuration for runtime environments."""
    manager: RuntimeManager
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
