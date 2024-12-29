"""Type definitions for runtime management."""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, NamedTuple
from datetime import datetime


class RuntimeManager(str, Enum):
    """Supported runtime managers."""
    NPX = "npx"
    BUNX = "bunx"
    UVX = "uvx"
    PIPX = "pipx"


class CaptureMode(str, Enum):
    """Output capture modes."""
    STDOUT = "stdout"
    STDERR = "stderr"
    BOTH = "both"
    NONE = "none"


class TestResult(str, Enum):
    """Possible test execution results."""
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class ResourceLimits:
    """Resource limits for an environment."""
    max_memory_mb: Optional[int] = None
    max_cpu_percent: Optional[float] = None
    timeout_seconds: Optional[int] = None


@dataclass(frozen=True)
class RuntimeConfig:
    """Configuration for a runtime environment."""
    manager: RuntimeManager
    package_name: str
    version: Optional[str] = None
    args: List[str] = ()
    env: Dict[str, str] = ()
    working_dir: Optional[str] = None
    resource_limits: Optional[ResourceLimits] = None


@dataclass(frozen=True)
class ProcessStats:
    """Statistics for a process execution."""
    peak_memory_mb: float
    avg_cpu_percent: float
    duration_seconds: float
    peak_cpu_percent: float


@dataclass(frozen=True)
class CaptureConfig:
    """Configuration for output capture."""
    mode: CaptureMode = CaptureMode.BOTH
    max_output_size: Optional[int] = None
    include_timestamps: bool = True
    include_stats: bool = True


@dataclass(frozen=True)
class CapturedOutput:
    """Captured process output."""
    stdout: str
    stderr: str
    exit_code: int
    start_time: datetime
    end_time: datetime
    stats: Optional[ProcessStats] = None


@dataclass(frozen=True)
class TestConfig:
    """Configuration for a test run."""
    name: str
    command: str
    expected_output: Optional[str] = None
    expected_exit_code: int = 0
    timeout_seconds: Optional[int] = None
    env: Dict[str, str] = ()
    capture_config: CaptureConfig = CaptureConfig()


@dataclass(frozen=True)
class TestRunResult:
    """Results from a test execution."""
    config: TestConfig
    result: TestResult
    captured: CapturedOutput
    error_message: Optional[str] = None
    failure_details: Optional[Dict[str, str]] = None


class RuntimeEnv(NamedTuple):
    """Active runtime environment details."""
    id: str
    config: RuntimeConfig
    created_at: datetime
    working_dir: str
    env_vars: Dict[str, str]