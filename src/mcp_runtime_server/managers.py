"""Runtime manager utilities."""

import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from mcp_runtime_server.types import RuntimeManager

logger = logging.getLogger(__name__)


def get_manager_binary(manager: RuntimeManager) -> str:
    """Get the path to the runtime manager binary.

    Args:
        manager: Runtime manager type

    Returns:
        Path to binary or command name

    Raises:
        RuntimeError: If manager binary not found
    """
    binary = shutil.which(manager.value)
    if not binary:
        raise RuntimeError(f"Runtime {manager.value} not found in PATH")
    return binary


def build_install_command(
    manager: RuntimeManager,
    package: str,
    version: Optional[str] = None,
    args: Optional[List[str]] = None,
) -> Tuple[str, List[str]]:
    """Build package installation command for a runtime manager.

    Args:
        manager: Runtime manager type
        package: Package name to install
        version: Optional version specification
        args: Additional arguments

    Returns:
        Tuple of (command, arguments list)

    Raises:
        RuntimeError: If manager is not supported
    """
    if args is None:
        args = []

    if manager == RuntimeManager.NODE:
        cmd = get_manager_binary("npm")
        return cmd, ["install", "--no-save", package, *args]

    elif manager == RuntimeManager.BUN:
        cmd = get_manager_binary(manager)
        return cmd, ["install", package, *args]

    elif manager == RuntimeManager.UV:
        cmd = get_manager_binary(manager)
        return cmd, ["sync", *args]

    else:
        raise RuntimeError(f"Unsupported runtime: {manager}")


def validate_package_name(manager: RuntimeManager, package: str) -> bool:
    """Validate package name format for a runtime manager.

    Args:
        manager: Runtime manager type
        package: Package name to validate

    Returns:
        True if package name is valid
    """
    if not package:
        return False

    if manager in (RuntimeManager.NODE, RuntimeManager.BUN):
        # NPM package naming rules
        return all(c.isalnum() or c in "-_@/." for c in package)

    elif manager == RuntimeManager.UV:
        # Python package naming rules
        return all(c.isalnum() or c in "-_." for c in package)

    return False


def prepare_env_vars(manager: RuntimeManager, base_env: Dict[str, str]) -> Dict[str, str]:
    """Prepare environment variables for a runtime manager.

    Args:
        manager: Runtime manager type
        base_env: Base environment variables

    Returns:
        Dict of environment variables
    """
    env = base_env.copy()

    if manager == RuntimeManager.NODE:
        env.update({
            "NODE_NO_WARNINGS": "1",
            "NPM_CONFIG_UPDATE_NOTIFIER": "false"
        })

    elif manager == RuntimeManager.BUN:
        env.update({
            "NO_INSTALL_HINTS": "1"
        })

    elif manager == RuntimeManager.UV:
        env.update({
            "VIRTUAL_ENV": env.get("VIRTUAL_ENV", ""),
            "PIP_NO_CACHE_DIR": "1"
        })

    return env


def cleanup_manager_artifacts(manager: RuntimeManager, working_dir: str) -> None:
    """Clean up artifacts left by a runtime manager.

    Args:
        manager: Runtime manager type
        working_dir: Working directory to clean
    """
    work_path = Path(working_dir)

    if manager in (RuntimeManager.NODE, RuntimeManager.BUN):
        # Clean Node/Bun artifacts
        patterns = ["node_modules", "package*.json", ".npm"]
        if manager == RuntimeManager.BUN:
            patterns.extend(["bun.lockb", ".bun"])

        for pattern in patterns:
            for path in work_path.glob(pattern):
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink(missing_ok=True)

    elif manager == RuntimeManager.UV:
        # Clean UV artifacts
        for pattern in [".venv", "__pycache__", "*.pyc"]:
            for path in work_path.glob(pattern):
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink(missing_ok=True)