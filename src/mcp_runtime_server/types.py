"""Core type definitions"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List
from tempfile import TemporaryDirectory

Runtime = Enum('Runtime', ['PYTHON', 'NODE', 'BUN'])
PackageManager = Enum('PackageManager', ['UV', 'NPM', 'BUN'])
TestFramework = Enum('TestFramework', ['PYTEST'])

@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime configuration"""
    name: Runtime
    config_files: list[str]
    package_manager: PackageManager
    env_setup: dict[str, str]
    binary_name: str

@dataclass(frozen=True)
class Sandbox:
    """Isolated execution environment"""
    root: Path
    work_dir: Path
    bin_dir: Path
    tmp_dir: Path
    cache_dir: Path
    temp_dir: TemporaryDirectory
    env_vars: dict[str, str]

@dataclass(frozen=True)
class Environment:
    """Runtime environment"""
    id: str
    runtime_config: RuntimeConfig
    created_at: datetime
    sandbox: Sandbox
    _pkg_bin: Path
    _runtime_bin: Path
    _test_bin: Path

    def __init__(self, id: str, runtime_config: RuntimeConfig, sandbox: Sandbox, created_at: datetime):
        object.__setattr__(self, 'id', id)
        object.__setattr__(self, 'runtime_config', runtime_config)
        object.__setattr__(self, 'sandbox', sandbox)
        object.__setattr__(self, 'created_at', created_at)
        object.__setattr__(self, '_pkg_bin', sandbox.bin_dir / runtime_config.package_manager.value.lower())
        object.__setattr__(self, '_runtime_bin', sandbox.bin_dir / runtime_config.binary_name)
        object.__setattr__(self, '_test_bin', sandbox.bin_dir / ("pytest" if runtime_config.name == Runtime.PYTHON else "jest"))

    @property
    def runtime(self) -> Runtime:
        return self.runtime_config.name

    @property
    def work_dir(self) -> Path:
        return self.sandbox.work_dir
        
    @property
    def pkg_bin(self) -> Path:
        return self._pkg_bin
        
    @property
    def runtime_bin(self) -> Path:
        return self._runtime_bin
        
    @property
    def test_bin(self) -> Path:
        return self._test_bin

@dataclass(frozen=True)
class ValidationResult:
    """Validation result with optional error details"""
    is_valid: bool
    errors: List[str] = None

@dataclass(frozen=True)
class RunConfig:
    """Test run configuration"""
    framework: TestFramework
    env: Environment
    test_dirs: List[Path]

@dataclass(frozen=True)
class TestCase:
    """Test execution result"""
    name: str
    status: str
    output: list[str]
    failure_message: str | None = None
    duration: float | None = None
