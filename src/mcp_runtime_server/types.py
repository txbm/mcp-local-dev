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

    @property
    def runtime(self) -> Runtime:
        return self.runtime_config.name

    @property
    def work_dir(self) -> Path:
        return self.sandbox.work_dir
        
    @property
    def pkg_bin(self) -> Path:
        return self.sandbox.bin_dir / self.runtime_config.package_manager.value.lower()
        
    @property
    def runtime_bin(self) -> Path:
        return self.sandbox.bin_dir / self.runtime_config.binary_name
        
    @property
    def test_bin(self) -> Path:
        return self.sandbox.bin_dir / ("pytest" if self.runtime == Runtime.PYTHON else "jest")

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
