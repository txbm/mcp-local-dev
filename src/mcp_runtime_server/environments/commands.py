"""Environment command execution."""
import asyncio
from typing import Dict, Optional

from mcp_runtime_server.environments.runtime import Runtime
from mcp_runtime_server.environments.environment import Environment
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)

async def run_command(
    cmd: str,
    cwd: str,
    env_vars: Optional[Dict[str, str]] = None
) -> asyncio.subprocess.Process:
    """Run a command in a working directory."""
    try:
        return await asyncio.create_subprocess_shell(
            cmd,
            cwd=cwd,
            env=env_vars,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    except Exception as e:
        raise RuntimeError(f"Command execution failed: {e}")

async def run_install(env: Environment) -> None:
    """Run install command for environment runtime."""
    if env.runtime == Runtime.PYTHON:
        cmd = "uv sync --all-extras"
    elif env.runtime == Runtime.NODE:
        cmd = "npm install"
    elif env.runtime == Runtime.BUN:
        cmd = "bun install"
    else:
        raise RuntimeError(f"Unsupported runtime: {env.runtime}")
        
    process = await run_command(cmd, str(env.work_dir), env.env_vars)
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        raise RuntimeError(
            f"Install failed with code {process.returncode}\n"
            f"stdout: {stdout.decode()}\n"
            f"stderr: {stderr.decode()}"
        )