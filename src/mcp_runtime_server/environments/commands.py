"""Environment command execution."""
import asyncio
from typing import Dict, Optional
from pathlib import Path

from mcp_runtime_server.types import Runtime, PackageManager, Environment
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
    pkg_manager = PackageManager.for_runtime(env.runtime)
    
    # Get the appropriate install command for package manager
    if pkg_manager == PackageManager.UV:
        cmd = "uv sync --all-extras"
    elif pkg_manager == PackageManager.NPM:
        cmd = "npm install"
    elif pkg_manager == PackageManager.BUN:
        cmd = "bun install"
    else:
        raise RuntimeError(f"Unsupported package manager: {pkg_manager}")
        
    process = await run_command(cmd, str(env.sandbox.work_dir), env.env_vars)
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
        branch: Optional branch to clone
        env_vars: Environment variables for git
    """
    try:
        logger.debug({
            "event": "preparing_clone",
            "url": url,
            "target_dir": str(target_dir)
        })
        
        # Ensure HTTPS URL
        if not url.startswith("https://"):
            if url.startswith("http://") or url.startswith("git@"):
                raise ValueError("Only HTTPS URLs are supported")
            url = f"https://{url}"
            
        logger.debug({
            "event": "clone_url_processed",
            "final_url": url
        })
        
        # Build command
        cmd = f"git clone {url} {target_dir}"
        if branch:
            cmd += f" -b {branch}"
            
        logger.debug({
            "event": "cloning_repository",
            "command": cmd,
            "target_dir": str(target_dir),
            "parent_dir": str(Path(target_dir).parent)
        })
            
        process = await run_command(
            cmd,
            str(Path(target_dir).parent),
            env_vars
        )
        stdout, stderr = await process.communicate()
        
        if stdout:
            logger.debug({
                "event": "clone_stdout",
                "output": stdout.decode()
            })
        if stderr:
            logger.debug({
                "event": "clone_stderr",
                "output": stderr.decode()
            })
            
        if process.returncode != 0:
            logger.error({
                "event": "clone_failed",
                "return_code": process.returncode,
                "stderr": stderr.decode()
            })
            raise RuntimeError(f"Failed to clone repository: {stderr.decode()}")
            
        logger.info({
            "event": "repository_cloned",
            "url": url,
            "target_dir": str(target_dir)
        })
            
    except Exception as e:
        logger.error({
            "event": "clone_error",
            "error": str(e)
        })
        raise RuntimeError(f"Clone failed: {str(e)}")