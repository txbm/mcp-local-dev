"""Sandbox creation and security."""

import os
import stat
import shutil
import platform
from pathlib import Path
from typing import Dict

from mcp_runtime_server.logging import get_logger
from mcp_runtime_server.types import Sandbox

logger = get_logger(__name__)


def create_sandbox(root: Path) -> Sandbox:
    """Create new sandbox environment within root directory."""
    try:
        dirs = _create_directories(root)
        env_vars = _prepare_environment(root, dirs)
        _apply_security(root)

        return Sandbox(
            root=root, work_dir=dirs["work"], bin_dir=dirs["bin"], env_vars=env_vars
        )
    except Exception as e:
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)
        raise RuntimeError(f"Failed to create sandbox: {e}")


def _create_directories(root: Path) -> Dict[str, Path]:
    """Create sandbox directory structure."""
    dirs = {
        "bin": root / "bin",
        "tmp": root / "tmp",
        "work": root / "work",
        "cache": root / "cache",
    }

    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)

    return dirs


def _prepare_environment(root: Path, dirs: Dict[str, Path]) -> Dict[str, str]:
    """Prepare sandbox environment variables."""
    env = os.environ.copy()

    env.update(
        {
            "TMPDIR": str(dirs["tmp"]),
            "XDG_CACHE_HOME": str(dirs["cache"]),
            "XDG_RUNTIME_DIR": str(dirs["tmp"]),
            "PATH": f"{dirs['bin']}{os.pathsep}{env.get('PATH', '')}",
        }
    )

    # Remove unsafe vars
    for var in ["LD_PRELOAD", "LD_LIBRARY_PATH"]:
        env.pop(var, None)

    return env


def _apply_security(root: Path) -> None:
    """Apply security restrictions."""
    if platform.system() == "Linux":
        _apply_unix_permissions(root)


def _apply_unix_permissions(path: Path) -> None:
    """Apply restrictive Unix permissions."""
    os.chmod(path, 0o600)

    if path.is_dir():
        for child in path.iterdir():
            _apply_unix_permissions(child)


def cleanup_sandbox(sandbox) -> None:
    """Clean up sandbox environment."""
    try:
        if sandbox.root.exists():
            shutil.rmtree(sandbox.root, ignore_errors=True)
    except Exception as e:
        raise RuntimeError(f"Failed to clean up sandbox: {e}")
