"""Core type definitions"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, NamedTuple
from tempfile import TemporaryDirectory

Runtime = Enum('Runtime', ['PYTHON', 'NODE', 'BUN'])
PackageManager = Enum('PackageManager', ['UV', 'NPM', 'BUN'])
TestFramework = Enum('TestFramework', ['PYTEST'])

def get_package_manager(runtime: Runtime) -> PackageManager:
    """Get default package manager for runtime"""
    if runtime == Runtime.PYTHON:
        return PackageManager.UV
    elif runtime == Runtime.NODE:
        return PackageManager.NPM
    elif runtime == Runtime.BUN:
        return PackageManager.BUN
    raise ValueError(f"No package manager for runtime: {runtime}")

@dataclass(frozen=True)
class PlatformInfo:
    """Platform details"""
    os_name: str 
    arch: str
    format: str
    node_platform: str
    bun_platform: str
    uv_platform: str

PlatformMapping = NamedTuple('PlatformMapping', [
    ('node', str),
    ('bun', str), 
    ('uv', str),
    ('archive_format', str),
    ('platform_template', str),
    ('binary_location', str)
])

@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime configuration"""
    name: Runtime
    config_files: list[str]
    package_manager: PackageManager
    env_setup: dict[str, str]
    bin_paths: list[str]
    binary_name: str
    url_template: str
    checksum_template: str
    platform_style: str = "simple"
    version_prefix: str = "v"

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
    pkg_bin: Path
    runtime_bin: Path
    test_bin: Path

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

@dataclass(frozen=True)
class RunTestResult:
    """Test run results"""
    success: bool
    framework: str
    passed: int | None = None
    failed: int | None = None
    skipped: int | None = None
    total: int | None = None
    failures: list[dict[str, Any]] = None
    warnings: list[str] = None
    test_cases: list[dict[str, Any]] = None
    stdout: str | None = None
    stderr: str | None = None
    error: str | None = None
