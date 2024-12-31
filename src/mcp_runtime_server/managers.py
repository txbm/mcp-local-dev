"""Runtime manager utilities."""

import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from mcp_runtime_server.types import RuntimeManager

logger = logging.getLogger(__name__)


def get_manager_binary(manager: RuntimeManager) -> str:
    binary = shutil.which(manager.value)
    if not binary:
        raise RuntimeError(f"Runtime {manager.value} not found in PATH")
    return binary


def build_install_command(
    manager: RuntimeManager,
    args: Optional[List[str]] = None,
) -> Tuple[str, List[str]]:
    if args is None:
        args = []

    if manager == RuntimeManager.NODE:
        cmd = shutil.which("npm")
        if not cmd:
            raise RuntimeError("npm not found in PATH")
        return cmd, ["install"]

    elif manager == RuntimeManager.BUN:
        cmd = get_manager_binary(manager)
        return cmd, ["install"]

    elif manager == RuntimeManager.UV:
        cmd = get_manager_binary(manager)
        return cmd, ["sync", "--all-extras"]

    raise RuntimeError(f"Unsupported runtime: {manager}")


def prepare_env_vars(manager: RuntimeManager, base_env: Dict[str, str]) -> Dict[str, str]:
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
    work_path = Path(working_dir)

    if manager in (RuntimeManager.NODE, RuntimeManager.BUN):
        patterns = ["node_modules", ".npm"]
        if manager == RuntimeManager.BUN:
            patterns.extend(["bun.lockb", ".bun"])

        for pattern in patterns:
            for path in work_path.glob(pattern):
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink(missing_ok=True)

    elif manager == RuntimeManager.UV:
        for pattern in [".venv", "__pycache__", "*.pyc"]:
            for path in work_path.glob(pattern):
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink(missing_ok=True)