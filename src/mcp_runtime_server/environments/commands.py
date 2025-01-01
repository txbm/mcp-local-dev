"""Environment command execution."""
import asyncio
from typing import Dict, Optional
from pathlib import Path

from mcp_runtime_server.types import Runtimes, Environment
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
    if env.runtime == Runtimes.PYTHON:
        cmd = "uv sync --all-extras"
    elif env.runtime == Runtimes.NODE:
        cmd = "npm install"
    elif env.runtime == Runtimes.BUN:
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

async def clone_repository(url: str, target_dir: Path, branch: Optional[str], env_vars: Dict[str, str]) -> None:
    """Clone a GitHub repository using HTTPS.
    
    Args:
        url: Repository URL
        target_dir: Clone target directory
        env_vars: Environment variables for git
    """
    try:
        logger.debug(f"Original URL: {url}")
        
        # Ensure HTTPS URL
        if not url.startswith("https://"):
            if url.startswith("http://") or url.startswith("git@"):
                raise ValueError("Only HTTPS URLs are supported")
            url = f"https://{url}"
            
        logger.debug(f"Final URL: {url}")
        cmd = f"git clone {url} {target_dir}"
        logger.info(f"Executing git clone command: {cmd}")
        logger.debug(f"Clone target directory: {target_dir}")
        logger.debug(f"Clone working directory: {str(Path(target_dir).parent)}")
        logger.debug(f"Clone environment variables: {env_vars}")
            
        process = await run_command(
            cmd,
            str(Path(target_dir).parent),
            env_vars
        )
        stdout, stderr = await process.communicate()
        
        if stdout:
            logger.debug(f"Clone stdout: {stdout.decode()}")
        if stderr:
            logger.debug(f"Clone stderr: {stderr.decode()}")
            
        if process.returncode != 0:
            logger.error(f"Clone failed with return code {process.returncode}")
            raise RuntimeError(f"Failed to clone repository: {stderr.decode()}")
            
        logger.info("Repository cloned successfully")
            
    except Exception as e:
        logger.error(f"Clone failed: {str(e)}")
        raise RuntimeError(f"Clone failed: {str(e)}")
