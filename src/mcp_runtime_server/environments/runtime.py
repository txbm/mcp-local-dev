"""Runtime configuration and management."""

import os
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Protocol

from mcp_runtime_server.types import Runtime, PackageManager
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


class RuntimeContext(Protocol):
    """Protocol defining required context for runtime operations."""

    work_dir: Path
    bin_dir: Path
    env_vars: Dict[str, str]


@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime configuration details."""

    config_files: List[str]  # Files that indicate this runtime
    package_manager: PackageManager  # Default package manager
    env_setup: Dict[str, str]  # Base environment variables
    bin_paths: List[str]  # Possible binary paths in priority order


RUNTIME_CONFIGS: Dict[Runtime, RuntimeConfig] = {
    Runtime.NODE: RuntimeConfig(
        config_files=["package.json"],
        package_manager=PackageManager.NPM,
        env_setup={
            "NODE_NO_WARNINGS": "1",
            "NPM_CONFIG_UPDATE_NOTIFIER": "false"
        },
        bin_paths=["node_modules/.bin"]
    ),
    Runtime.BUN: RuntimeConfig(
        config_files=["bun.lockb", "package.json"],
        package_manager=PackageManager.BUN,
        env_setup={"NO_INSTALL_HINTS": "1"},
        bin_paths=["node_modules/.bin"]
    ),
    Runtime.PYTHON: RuntimeConfig(
        config_files=["pyproject.toml", "setup.py", "requirements.txt"],
        package_manager=PackageManager.UV,
        env_setup={
            "PIP_NO_CACHE_DIR": "1",
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1"
        },
        bin_paths=[".venv/bin", ".venv/Scripts"]  # Scripts for Windows
    )
}


def detect_runtime(work_dir: Path) -> Runtime:
    """Detect runtime from project files.
    
    Args:
        work_dir: Working directory containing project files
        
    Returns:
        Detected runtime type
        
    Raises:
        ValueError: If no supported runtime is detected
    """
    logger.debug({
        "event": "detecting_runtime",
        "work_dir": str(work_dir)
    })
    
    # Get all files in the directory
    files = set(str(p) for p in work_dir.rglob("*"))
    logger.debug({
        "event": "found_project_files",
        "files": list(files)
    })

    # Check each runtime's config files
    for runtime, config in RUNTIME_CONFIGS.items():
        # For runtimes that need all config files
        if runtime == Runtime.BUN:
            if all(any(f.endswith(c) for f in files) for c in config.config_files):
                logger.info({
                    "event": "runtime_detected",
                    "runtime": runtime.value,
                    "matched_files": config.config_files
                })
                return runtime
        # For runtimes that need any config file
        else:
            if any(any(f.endswith(c) for f in files) for c in config.config_files):
                logger.info({
                    "event": "runtime_detected", 
                    "runtime": runtime.value,
                    "matched_file": next(
                        c for c in config.config_files 
                        if any(f.endswith(c) for f in files)
                    )
                })
                return runtime

    logger.error({
        "event": "no_runtime_detected",
        "work_dir": str(work_dir)
    })
    raise ValueError("No supported runtime detected")


def get_binary_path(name: str, ctx: RuntimeContext) -> Optional[Path]:
    """Get path to a binary in the runtime context.
    
    Args:
        name: Binary name to find
        ctx: Runtime context containing paths
        
    Returns:
        Path to binary if found, None otherwise
    """
    # First check if it's in the PATH
    system_bin = shutil.which(name, path=ctx.env_vars.get("PATH"))
    if system_bin:
        return Path(system_bin)

    # Then check runtime bin directory
    if ctx.bin_dir:
        bin_path = ctx.bin_dir / name
        if not bin_path.exists() and os.name == "nt":
            bin_path = ctx.bin_dir / f"{name}.exe"
        if bin_path.exists():
            return bin_path

    return None


def setup_runtime_env(runtime: Runtime, ctx: RuntimeContext) -> Dict[str, str]:
    """Setup runtime environment variables.
    
    Args:
        runtime: Runtime type to configure
        ctx: Runtime context with paths and base env
        
    Returns:
        Dict of environment variables
    """
    logger.debug({
        "event": "setting_up_runtime_env",
        "runtime": runtime.value,
        "work_dir": str(ctx.work_dir)
    })

    env = ctx.env_vars.copy()
    config = RUNTIME_CONFIGS[runtime]

    # Add runtime-specific vars
    env.update(config.env_setup)

    # Runtime-specific setup
    if runtime == Runtime.PYTHON:
        venv = ctx.work_dir / ".venv"
        env.update({
            "VIRTUAL_ENV": str(venv),
            "PYTHONPATH": str(ctx.work_dir)
        })
    elif runtime in (Runtime.NODE, Runtime.BUN):
        env["NODE_PATH"] = str(ctx.work_dir / "node_modules")

    logger.debug({
        "event": "runtime_env_configured",
        "runtime": runtime.value,
        "env_vars": {k: v for k, v in env.items() if k in config.env_setup}
    })

    return env