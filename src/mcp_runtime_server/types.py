"""Core type definitions."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List
from tempfile import TemporaryDirectory


class Runtime(str, Enum):
    """Runtime environment types."""

    PYTHON = "python"
    NODE = "node"
    BUN = "bun"


class PackageManager(str, Enum):
    """Package manager types."""

    UV = "uv"  # Python
    NPM = "npm"  # Node.js
    BUN = "bun"  # Bun

    @classmethod
    def for_runtime(cls, runtime: Runtime) -> "PackageManager":
        """Get default package manager for runtime."""
        if runtime == Runtime.PYTHON:
            return cls.UV
        elif runtime == Runtime.NODE:
            return cls.NPM
        elif runtime == Runtime.BUN:
            return cls.BUN
        raise ValueError(f"No package manager for runtime: {runtime}")


@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime configuration details."""
    config_files: List[str]  # Files that indicate this runtime
    package_manager: PackageManager  # Default package manager
    env_setup: Dict[str, str]  # Base environment variables
    bin_paths: List[str]  # Possible binary paths in priority order


@dataclass(frozen=True)
class RuntimeContext:
    """Context for runtime operations."""
    work_dir: Path
    bin_dir: Path
    env_vars: Dict[str, str]


@dataclass(frozen=True)
class Sandbox:
    root: Path
    work_dir: Path
    bin_dir: Path
    env_vars: Dict[str, str]


@dataclass(frozen=True)
class Environment:
    """Runtime environment instance."""

    id: str
    runtime: Runtime
    work_dir: Path
    created_at: datetime
    env_vars: Dict[str, str]
    sandbox: Sandbox
    tempdir: TemporaryDirectory


@dataclass
class TestCase:
    """Test case execution result."""
    name: str
    status: str
    output: List[str]
    failure_message: Optional[str] = None
    duration: Optional[float] = None


@dataclass
class RunTestResult:
    """Results from a test framework run."""
    success: bool
    framework: str
    passed: Optional[int] = None
    failed: Optional[int] = None
    skipped: Optional[int] = None
    total: Optional[int] = None
    failures: List[Dict[str, Any]] = None
    warnings: List[str] = None
    test_cases: List[Dict[str, Any]] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    error: Optional[str] = None

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.failures is None:
            self.failures = []
        if self.warnings is None:
            self.warnings = []
        if self.test_cases is None:
            self.test_cases = []