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
    binary_name: str  # Name of the runtime binary
    url_template: str  # Download URL template
    checksum_template: Optional[str]  # Optional checksum URL template
    platform_style: str = "simple"  # Platform string style (simple or composite)
    version_prefix: str = "v"  # Version number prefix in URLs
    github_release: bool = False  # Whether this uses GitHub releases
    owner: Optional[str] = None  # GitHub owner for releases
    repo: Optional[str] = None  # GitHub repo for releases


RUNTIME_CONFIGS: Dict[Runtime, RuntimeConfig] = {
    Runtime.NODE: RuntimeConfig(
        config_files=["package.json"],
        package_manager=PackageManager.NPM,
        env_setup={
            "NODE_NO_WARNINGS": "1",
            "NPM_CONFIG_UPDATE_NOTIFIER": "false"
        },
        bin_paths=["node_modules/.bin"],
        binary_name="node",
        url_template="https://nodejs.org/dist/{version_prefix}{version}/node-{version_prefix}{version}-{platform}-{arch}.{format}",
        checksum_template="https://nodejs.org/dist/{version_prefix}{version}/SHASUMS256.txt"
    ),
    Runtime.BUN: RuntimeConfig(
        config_files=["bun.lockb", "package.json"],
        package_manager=PackageManager.BUN,
        env_setup={"NO_INSTALL_HINTS": "1"},
        bin_paths=["node_modules/.bin"],
        binary_name="bun",
        url_template="https://github.com/oven-sh/bun/releases/download/bun-{version_prefix}{version}/bun-{platform}-{arch}.{format}",
        checksum_template="https://github.com/oven-sh/bun/releases/download/bun-{version_prefix}{version}/SHASUMS.txt",
        github_release=True
    ),
    Runtime.PYTHON: RuntimeConfig(
        config_files=["pyproject.toml", "setup.py", "requirements.txt"],
        package_manager=PackageManager.UV,
        env_setup={
            "PIP_NO_CACHE_DIR": "1",
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1"
        },
        bin_paths=[".venv/bin", ".venv/Scripts"],  # Scripts for Windows
        binary_name="uv",
        url_template="https://github.com/{owner}/{repo}/releases/download/{version_prefix}{version}/uv-{platform}.{format}",
        checksum_template=None,
        platform_style="composite",
        version_prefix="",
        github_release=True,
        owner="astral-sh",
        repo="uv"
    )
}


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