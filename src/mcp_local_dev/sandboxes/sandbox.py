"""Sandbox directory and command execution management."""

import tempfile
import asyncio
import sys
import shutil
from pathlib import Path

from mcp_local_dev.types import Sandbox, PackageManager
from mcp_local_dev.logging import get_logger

logger = get_logger(__name__)


def get_system_paths() -> str:
    """Get essential system binary paths for the current platform."""
    if sys.platform == "darwin":
        return "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    elif sys.platform == "linux":
        return "/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin"
    else:
        raise RuntimeError(f"Unsupported platform: {sys.platform}")


async def create_sandbox(prefix: str) -> Sandbox:
    """Create new sandbox environment with isolated directories.

    Args:
        prefix: Prefix for temporary directory name

    Returns:
        Sandbox instance

    Raises:
        RuntimeError: If sandbox creation fails
    """
    # Create temporary directory that will be cleaned up on exit
    temp_dir = tempfile.TemporaryDirectory(prefix=prefix, delete=False)
    root = Path(temp_dir.name)

    # Create sandbox directory structure
    dirs = {
        "bin": root / "bin",
        "tmp": root / "tmp",
        "work": root / "work",
        "cache": root / "cache",
    }

    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)

    # Set up isolated environment variables with sanitized PATH
    env_vars = {
        "PATH": f"{dirs['bin']}:{get_system_paths()}",  # Only include sandbox bin + essential system paths
        "TMPDIR": str(dirs["tmp"]),
        "HOME": str(dirs["work"]),
        "XDG_CACHE_HOME": str(dirs["cache"]),
        "XDG_RUNTIME_DIR": str(dirs["tmp"]),
    }

    sandbox = Sandbox(
        root=root,
        work_dir=dirs["work"],
        bin_dir=dirs["bin"],
        tmp_dir=dirs["tmp"],
        cache_dir=dirs["cache"],
        env_vars=env_vars,
        temp_dir=temp_dir,
    )

    logger.info(
        {"event": "sandbox_created", "root": str(root), "work_dir": str(dirs["work"])}
    )

    return sandbox


def add_package_manager_bin_path(sandbox: Sandbox, pkg_manager: PackageManager) -> None:
    """Add package manager's bin directory to sandbox PATH"""
    pkg_bin_path = None
    match pkg_manager:
        case PackageManager.UV:
            pkg_bin_path = sandbox.work_dir / ".venv" / "bin"
        case PackageManager.NPM | PackageManager.BUN:
            pkg_bin_path = sandbox.work_dir / "node_modules" / ".bin"

    if pkg_bin_path:
        current_path = sandbox.env_vars["PATH"]
        sandbox.env_vars["PATH"] = f"{pkg_bin_path}:{current_path}"
        logger.debug(
            {
                "event": "updated_sandbox_path",
                "package_manager": pkg_manager.value,
                "bin_path": str(pkg_bin_path),
            }
        )


def cleanup_sandbox(sandbox: Sandbox) -> None:
    """Clean up sandbox environment.

    Args:
        sandbox: Sandbox instance to clean up
    """
    logger.debug({"event": "cleaning_sandbox", "root": str(sandbox.root)})
    # sandbox.temp_dir.cleanup()


async def run_sandboxed_command(
    sandbox: Sandbox, cmd: str, env_vars: dict[str, str] | None = None
) -> asyncio.subprocess.Process:
    """Run command in sandbox environment."""
    cmd_env = {**sandbox.env_vars, **(env_vars or {})}

    if not shutil.which(cmd.split()[0]):
        raise ValueError(f"Command not found: {cmd.split()[0]}")

    logger.debug({"event": "sandbox_cmd_exec", "cmd": cmd})

    process = await asyncio.create_subprocess_shell(
        cmd,
        cwd=sandbox.work_dir,
        env=cmd_env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Create wrapper class to intercept and log output
    class LoggingPipe:
        def __init__(self, pipe, event_type):
            self.pipe = pipe
            self.event_type = event_type
            
        async def read(self):
            data = await self.pipe.read()
            if data:
                logger.debug(
                    {"event": f"sandbox_cmd_{self.event_type}", 
                     "cmd": cmd, 
                     "output": data.decode()}
                )
            return data

    # Wrap stdout/stderr with logging interceptors
    if process.stdout:
        process._stdout = LoggingPipe(process.stdout, "stdout")
    if process.stderr:
        process._stderr = LoggingPipe(process.stderr, "stderr")

    # Add completion callback
    orig_wait = process.wait
    async def logging_wait():
        code = await orig_wait()
        logger.debug(
            {"event": "sandbox_cmd_complete", "cmd": cmd, "returncode": code}
        )
        return code
    process.wait = logging_wait

    return process
