"""Runtime server type definitions."""
from typing import TypeAlias, Optional, Dict, Any, NamedTuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


RuntimeManager = Enum('RuntimeManager', [
    ('NODE', 'node'),
    ('BUN', 'bun'),
    ('UV', 'uv')
])


@dataclass(frozen=True)
class ResourceLimits:
    """Resource limits for runtime environments."""
    max_memory_mb: Optional[int] = None
    max_cpu_percent: Optional[float] = None
    timeout_seconds: Optional[int] = None


CaptureMode = Enum('CaptureMode', [
    ('STDOUT', 'stdout'),
    ('STDERR', 'stderr'),
    ('BOTH', 'both')
])


@dataclass(frozen=True)
class CaptureConfig:
    """Configuration for output capture."""
    mode: CaptureMode = CaptureMode.BOTH
    max_output_size: Optional[int] = None
    include_timestamps: bool = False
    include_stats: bool = True


@dataclass(frozen=True)
class RuntimeConfig:
    """Configuration for runtime environments."""
    manager: RuntimeManager
    package_name: str
    version: Optional[str] = None
    args: list[str] = None
    env: Dict[str, str] = None
    working_dir: Optional[str] = None
    resource_limits: Optional[ResourceLimits] = None

    def __post_init__(self):
        object.__setattr__(self, 'args', self.args or [])
        object.__setattr__(self, 'env', self.env or {})


@dataclass(frozen=True)
class RuntimeEnv:
    """Runtime environment state."""
    id: str
    config: RuntimeConfig
    created_at: datetime
    working_dir: str
    env_vars: Dict[str, str]


class TestConfig(NamedTuple):
    """Test configuration for runtime environments."""
    name: str
    config: RuntimeConfig

RuntimeExitCode: TypeAlias = int
RuntimeOutput: TypeAlias = str
RuntimeEnvVars: TypeAlias = Dict[str, str]

def runtime_error(message: str, details: Optional[Dict[str, Any]] = None) -> Exception:
    """Create a runtime error with optional details."""
    err = Exception(message)
    if details:
        setattr(err, 'details', details)
    return err
