"""Runtime server type definitions."""
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


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


@dataclass(frozen=True)
class Environment:
    """Runtime environment state."""
    id: str
    config: RuntimeConfig
    created_at: datetime
    working_dir: str
