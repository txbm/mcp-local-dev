"""Runtime detection and configuration."""

import shutil
from typing import Dict

from mcp_local_dev.types import Runtime, PackageManager, RuntimeConfig, Sandbox
from mcp_local_dev.logging import get_logger
from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command, add_package_manager_bin_path
from mcp_local_dev.sandboxes.commands import install_packages

logger = get_logger(__name__)


RUNTIME_CONFIGS: Dict[Runtime, RuntimeConfig] = {
    Runtime.NODE: RuntimeConfig(
        name=Runtime.NODE,
        config_files=["package.json"],
        package_manager=PackageManager.NPM,
        env_setup={"NODE_NO_WARNINGS": "1"},
        binary_name="node",
    ),
    Runtime.BUN: RuntimeConfig(
        name=Runtime.BUN,
        config_files=["bun.lockb", "package.json"],
        package_manager=PackageManager.BUN,
        env_setup={"NO_INSTALL_HINTS": "1"},
        binary_name="bun",
    ),
    Runtime.PYTHON: RuntimeConfig(
        name=Runtime.PYTHON,
        config_files=["pyproject.toml", "setup.py", "requirements.txt"],
        package_manager=PackageManager.UV,
        env_setup={
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        binary_name="python",
    ),
}


def detect_runtime(sandbox: Sandbox) -> RuntimeConfig:
    """Detect runtime from project files."""
    work_dir = sandbox.work_dir
    
    SKIP_DIRS = {'.git', '.svn', '.hg', '.pytest_cache', '__pycache__', 'node_modules', '.venv'}
    
    files = {
        str(p.relative_to(work_dir))
        for p in work_dir.rglob("*")
        if not any(part.startswith('.') or part in SKIP_DIRS for part in p.parts)
    }

    for runtime, config in RUNTIME_CONFIGS.items():
        if any(any(f.endswith(c) for f in files) for c in config.config_files):
            return config

    raise ValueError("No supported runtime detected")


async def install_runtime(sandbox: Sandbox, config: RuntimeConfig) -> None:
    """Install runtime by setting up package manager and installing dependencies"""
    # Only symlink package manager binaries from host system
    if config.package_manager == PackageManager.UV:
        required_binaries = ['uv']
    elif config.package_manager == PackageManager.NPM:
        required_binaries = ['npm']
    elif config.package_manager == PackageManager.BUN:
        required_binaries = ['bun']
    else:
        raise RuntimeError(f"Unsupported package manager: {config.package_manager}")
        
    # Verify and symlink package manager
    missing = [bin for bin in required_binaries if not shutil.which(bin)]
    if missing:
        raise RuntimeError(f"Required package manager not found: {', '.join(missing)}")

    # Create symlinks to package manager in sandbox bin directory
    for binary in required_binaries:
        host_path = shutil.which(binary)
        if host_path:
            target = sandbox.bin_dir / binary
            if not target.exists():
                target.symlink_to(host_path)

    # Set up environment variables
    for key, value in config.env_setup.items():
        sandbox.env_vars[key] = value

    # Add package manager bin paths before installing packages
    add_package_manager_bin_path(sandbox, config.package_manager)

    # Install project dependencies (uv sync will create venv automatically)
    await install_packages(sandbox, config.package_manager)
        
