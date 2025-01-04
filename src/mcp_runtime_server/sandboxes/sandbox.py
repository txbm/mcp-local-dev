"""Sandbox directory and command execution management."""

import json
import tempfile
import asyncio
import os
import shutil
from pathlib import Path
from typing import Dict, Optional

from mcp_runtime_server.types import Sandbox
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


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
    temp_dir = tempfile.TemporaryDirectory(prefix=prefix)
    root = Path(temp_dir.name)

    # Create sandbox directory structure
    dirs = {
        "bin": root / "bin",
        "tmp": root / "tmp", 
        "work": root / "work",
        "cache": root / "cache"
    }
    
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
        
    # Set up isolated environment variables
    env_vars = {
        "PATH": f"{dirs['bin']}:{os.environ['PATH']}", # Sandbox bin + system PATH
        "TMPDIR": str(dirs["tmp"]),
        "HOME": str(dirs["work"]), 
        "XDG_CACHE_HOME": str(dirs["cache"]),
        "XDG_RUNTIME_DIR": str(dirs["tmp"])
    }

    sandbox = Sandbox(
        root=root,
        work_dir=dirs["work"],
        bin_dir=dirs["bin"],
        tmp_dir=dirs["tmp"],
        cache_dir=dirs["cache"],
        env_vars=env_vars,
        temp_dir=temp_dir
    )

    logger.info({
        "event": "sandbox_created",
        "root": str(root),
        "work_dir": str(dirs["work"])
    })

    return sandbox


def cleanup_sandbox(sandbox: Sandbox) -> None:
    """Clean up sandbox environment.
    
    Args:
        sandbox: Sandbox instance to clean up
    """
    logger.debug({"event": "cleaning_sandbox", "root": str(sandbox.root)})
    sandbox.temp_dir.cleanup()


async def run_sandboxed_command(
    sandbox: Sandbox,
    cmd: str,
    env_vars: Optional[Dict[str, str]] = None
) -> asyncio.subprocess.Process:
    """Run a command inside sandbox environment.
    
    Args:
        sandbox: Sandbox to run command in
        cmd: Command string to execute
        env_vars: Additional environment variables
        
    Returns:
        Process handle
        
    Raises:
        RuntimeError: If command execution fails
    """
    # Merge sandbox env with any additional vars
    cmd_env = sandbox.env_vars.copy()
    if env_vars:
        cmd_env.update(env_vars)

    logger.debug({
        "event": "sandbox_cmd_exec",
        "cmd": cmd,
        "cwd": str(sandbox.work_dir),
        "env": json.dumps(cmd_env)
    })

    # Check if command exists
    cmd_parts = cmd.split()
    if not shutil.which(cmd_parts[0]):
        raise RuntimeError(f"Command not found: {cmd_parts[0]}")
        
    return await asyncio.create_subprocess_shell(
        cmd,
        cwd=sandbox.work_dir,
        env=cmd_env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
