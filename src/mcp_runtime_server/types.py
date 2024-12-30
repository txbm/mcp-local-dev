"""Runtime server type definitions."""
from typing import TypeAlias, Optional, Dict, Any, NamedTuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto


class ManagerType(Enum):
    """Type of runtime manager."""
    BINARY = auto()  # Standalone binary managers like Node, Bun
    PYTHON = auto()  # Python-specific managers like UV


@dataclass(frozen=True)
class RuntimeManagerConfig:
    """Configuration for a runtime manager."""
    name: str
    type: ManagerType


class RuntimeManager(Enum):
    """Available runtime managers."""
    NODE = RuntimeManagerConfig(name='node', type=ManagerType.BINARY)
    BUN = RuntimeManagerConfig(name='bun', type=ManagerType.BINARY)
    UV = RuntimeManagerConfig(name='uv', type=ManagerType.PYTHON)

    @property
    def value(self) -> str:
        return self._value_.name

    @property
    def config(self) -> RuntimeManagerConfig:
        return self._value_


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


@dataclass(frozen=True)
class TestConfig:
    """Test configuration for runtime environments."""
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
class TestRunResult:
    """Results from a test run."""
    config: TestConfig
    result: TestResult
    captured: CapturedOutput
    error_message: Optional[str] = None
    failure_details: Optional[Dict[str, str]] = None


RuntimeExitCode: TypeAlias = int
RuntimeOutput: TypeAlias = str
RuntimeEnvVars: TypeAlias = Dict[str, str]


def runtime_error(message: str, details: Optional[Dict[str, Any]] = None) -> Exception:
    """Create a runtime error with optional details."""
    err = Exception(message)
    if details:
        setattr(err, 'details', details)
    return err