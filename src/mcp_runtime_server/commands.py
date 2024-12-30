"""Command execution utilities."""
import asyncio
from typing import Dict

from mcp_runtime_server.types import Environment


async def run_command(
    command: str,
    cwd: str,
    env_vars: Dict[str, str]
) -> asyncio.subprocess.Process:
    """Run a command with specific working directory and environment."""
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env_vars
        )
        
        return process
        
    except Exception as e:
        raise RuntimeError(f"Failed to run command: {e}")
