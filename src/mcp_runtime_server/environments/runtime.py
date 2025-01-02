"""Runtime configuration and management."""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from mcp_runtime_server.types import Runtime, PackageManager, RuntimeConfig
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


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


def find_binary(name: str, paths: List[str], env_path: Optional[str] = None) -> Optional[Path]:
    """Find a binary in the given paths.
    
    Args:
        name: Binary name to find
        paths: List of paths to search
        env_path: Optional PATH environment variable
        
    Returns:
        Path to binary if found, None otherwise
    """
    # Check system PATH first if provided
    if env_path:
        system_bin = shutil.which(name, path=env_path)
        if system_bin:
            return Path(system_bin)

    # Check provided paths
    for path in paths:
        bin_path = Path(path) / name
        if not bin_path.exists() and os.name == "nt":
            bin_path = Path(path) / f"{name}.exe"
        if bin_path.exists():
            return bin_path

    return None


def make_runtime_env(runtime: Runtime, work_dir: Path, base_env: Dict[str, str]) -> Dict[str, str]:
    """Create runtime environment variables.
    
    Args:
        runtime: Runtime type to configure
        work_dir: Working directory
        base_env: Base environment variables
        
    Returns:
        Dict of environment variables
    """
    logger.debug({
        "event": "creating_runtime_env",
        "runtime": runtime.value,
        "work_dir": str(work_dir)
    })

    env = base_env.copy()
    config = RUNTIME_CONFIGS[runtime]

    # Add runtime-specific base vars
    env.update(config.env_setup)

    # Add runtime-specific path vars
    if runtime == Runtime.PYTHON:
        venv = work_dir / ".venv"
        env.update({
            "VIRTUAL_ENV": str(venv),
            "PYTHONPATH": str(work_dir)
        })
    elif runtime in (Runtime.NODE, Runtime.BUN):
        env["NODE_PATH"] = str(work_dir / "node_modules")

    logger.debug({
        "event": "runtime_env_created",
        "runtime": runtime.value,
        "env_vars": {k: v for k, v in env.items() if k in config.env_setup}
    })

    return env