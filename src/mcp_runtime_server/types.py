"""Runtime server type definitions."""
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class RuntimeManager(str, Enum):
    """Runtime managers supported by the server."""
    NODE = "node"
    BUN = "bun"
    UV = "uv"


class ResourceLimits(BaseModel):
    """Resource limits for runtime environments."""
    max_memory_mb: Optional[int] = None
    max_cpu_percent: Optional[float] = None
    timeout_seconds: Optional[int] = None

    model_config = ConfigDict(extra="allow")


class CaptureMode(str, Enum):
    """Output capture modes."""
    STDOUT = "stdout"
    STDERR = "stderr"
    BOTH = "both"


class CaptureConfig(BaseModel):
    """Configuration for output capture."""
    mode: CaptureMode = CaptureMode.BOTH
    max_output_size: Optional[int] = None
    include_timestamps: bool = False
    include_stats: bool = True

    model_config = ConfigDict(extra="allow")


class RuntimeConfig(BaseModel):
    """Configuration for runtime environments."""
    manager: RuntimeManager
    package_name: str
    version: Optional[str] = None
    args: list[str] = []
    env: Dict[str, str] = {}
    working_dir: Optional[str] = None
    resource_limits: Optional[ResourceLimits] = None

    model_config = ConfigDict(extra="allow")


class RuntimeEnv(BaseModel):
    """Runtime environment state."""
    id: str
    config: RuntimeConfig
    created_at: datetime
    working_dir: str
    env_vars: Dict[str, str]

    model_config = ConfigDict(extra="allow")


class RuntimeError(Exception):
    """Base class for runtime errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}