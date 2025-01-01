"""Runtime detection and configuration."""

import shutil
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from mcp_runtime_server.types import Runtime, PackageManager
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime configuration details."""

    config_files: List[str]
    env_vars: Dict[str, str]
    bin_path: str


CONFIGS = {
    Runtime.NODE: RuntimeConfig(
        config_files=["package.json"],
        env_vars={"NODE_NO_WARNINGS": "1", "NPM_CONFIG_UPDATE_NOTIFIER": "false"},
        bin_path="node_modules/.bin",
    ),
    Runtime.BUN: RuntimeConfig(
        config_files=["bun.lockb", "package.json"],
        env_vars={"NO_INSTALL_HINTS": "1"},
        bin_path="node_modules/.bin",
    ),
    Runtime.PYTHON: RuntimeConfig(
        config_files=["pyproject.toml", "setup.py"],
        env_vars={"VIRTUAL_ENV": "", "PIP_NO_CACHE_DIR": "1"},
        bin_path=".venv/bin",
    ),
}


def detect_runtime(work_dir: Path) -> Runtime:
    """Detect runtime from project files."""
    files = set(str(p) for p in work_dir.rglob("*"))

    # Check Bun first (requires both files)
    if all(
        any(f.endswith(c) for f in files) for c in CONFIGS[Runtime.BUN].config_files
    ):
        return Runtime.BUN

    # Then Node
    if any(f.endswith("package.json") for f in files):
        return Runtime.NODE

    # Finally Python
    if any(
        any(f.endswith(c) for f in files) for c in CONFIGS[Runtime.PYTHON].config_files
    ):
        return Runtime.PYTHON

    raise ValueError("No supported runtime detected")


def get_package_manager_binary(pkg_manager: PackageManager) -> str:
    """Get package manager binary path."""
    binary = shutil.which(pkg_manager.value)
    if not binary:
        raise RuntimeError(f"Package manager {pkg_manager.value} not found")
    return binary


def get_runtime_bin_dir(work_dir: Path, runtime: Runtime) -> Path:
    """Get runtime binary directory."""
    bin_path = work_dir / CONFIGS[runtime].bin_path
    platform_bin = bin_path / "Scripts" if os.name == "nt" else bin_path
    return platform_bin if platform_bin.exists() else bin_path


def setup_runtime_env(
    base_env: Dict[str, str], runtime: Runtime, work_dir: Path
) -> Dict[str, str]:
    """Setup runtime environment variables."""
    env = base_env.copy()
    bin_dir = get_runtime_bin_dir(work_dir, runtime)

    # Base PATH setup
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"

    # Runtime-specific vars
    runtime_vars = CONFIGS[runtime].env_vars.copy()
    if runtime == Runtime.PYTHON:
        venv = work_dir / ".venv"
        runtime_vars["VIRTUAL_ENV"] = str(venv)
        runtime_vars["PYTHONPATH"] = str(work_dir)
    elif runtime in (Runtime.NODE, Runtime.BUN):
        runtime_vars["NODE_PATH"] = str(work_dir / "node_modules")

    env.update(runtime_vars)
    return env
