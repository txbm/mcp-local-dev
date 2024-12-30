"""Execution utilities."""
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict

from mcp_runtime_server.commands import run_command
from mcp_runtime_server.types import Environment


async def auto_run_tests(
    env: Environment,
    cwd: str,
    env_vars: Optional[Dict[str, str]] = None
) -> None:
    """Automatically run tests based on project structure."""
    base_env = env_vars or {}
    test_env = {**base_env, "PYTHONPATH": str(Path(cwd))}
    
    pytest_cmd = "pytest"
    
    try:
        process = await run_command(pytest_cmd, cwd, test_env)
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logging.error(f"Tests failed with code {process.returncode}")
            logging.error(stderr.decode())
            raise RuntimeError("Tests failed")
            
    except Exception as e:
        raise RuntimeError(f"Failed to run tests: {e}")
