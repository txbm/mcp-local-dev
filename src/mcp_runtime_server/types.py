"""Runtime server type definitions."""
from typing import TypeAlias, Optional, Dict, Any
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
class Environment:
    """Runtime environment state."""
    id: str
    config: RuntimeConfig
    created_at: datetime
    working_dir: str
    env_vars: Dict[str, str]


@dataclass(frozen=True)
class TestConfig:
    """Test configuration."""
    name: str
    command: str
    timeout_seconds: int = 30
    expected_exit_code: int = 0
    expected_output: Optional[str] = None


TestResult = Enum('TestResult', [
    ('PASS', 'pass'),
    ('FAIL', 'fail'),
    ('ERROR', 'error'),
    ('TIMEOUT', 'timeout')
])


@dataclass(frozen=True)
class CapturedOutput:
    """Output captured from test execution."""
    stdout: str
    stderr: str
    exit_code: int
    start_time: datetime
    end_time: datetime


@dataclass(frozen=True)
class TestResult:
    """Results from a test run."""
    config: TestConfig
    result: TestResult
    captured: CapturedOutput
    error_message: Optional[str] = None
    failure_details: Optional[Dict[str, str]] = None


ExitCode: TypeAlias = int 
Stdout: TypeAlias = str
Stderr: TypeAlias = str
EnvVars: TypeAlias = Dict[str, str]

def error(message: str, details: Optional[Dict[str, Any]] = None) -> Exception:
    """Create an error with optional details."""
    err = Exception(message)
    if details:
        setattr(err, 'details', details)
    return err