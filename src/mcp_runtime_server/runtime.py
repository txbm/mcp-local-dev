"""Runtime environment management."""
import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict
import tempfile

from mcp_runtime_server.types import RuntimeConfig, Environment

logger = logging.getLogger(__name__)

# Active environments
ENVIRONMENTS: Dict[str, Environment] = {}


def _get_git_root_dir() -> Path:
    """Get Git root directory for storing repositories."""
    root = Path(tempfile.gettempdir()) / "mcp-runtime" / "repos"
    root.mkdir(parents=True, exist_ok=True)
    return root


async def create_environment(config: RuntimeConfig) -> Environment:
    """Create a new runtime environment."""
    try:
        # Create unique working directory
        env_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        work_dir = _get_git_root_dir() / env_id
        work_dir.mkdir(parents=True)
        
        # Clone repository
        process = await asyncio.create_subprocess_exec(
            "git", "clone", config.github_url, str(work_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise ValueError(f"Failed to clone repository: {stderr.decode()}")

        # Create environment
        env = Environment(
            id=env_id,
            config=config,
            created_at=datetime.utcnow(),
            working_dir=str(work_dir)
        )
        
        ENVIRONMENTS[env.id] = env
        return env
        
    except Exception as e:
        if 'work_dir' in locals() and work_dir.exists():
            import shutil
            shutil.rmtree(str(work_dir))
        raise ValueError(f"Failed to create environment: {e}") from e


async def cleanup_environment(env_id: str) -> None:
    """Clean up a runtime environment."""
    if env_id not in ENVIRONMENTS:
        return
        
    env = ENVIRONMENTS[env_id]
    work_dir = Path(env.working_dir)
    
    try:
        # Clean up working directory
        if work_dir.exists():
            import shutil
            shutil.rmtree(str(work_dir))
            
    finally:
        del ENVIRONMENTS[env_id]


async def run_command(env_id: str, command: str) -> asyncio.subprocess.Process:
    """Run a command in an environment."""
    if env_id not in ENVIRONMENTS:
        raise ValueError(f"Unknown environment: {env_id}")
        
    env = ENVIRONMENTS[env_id]
    
    try:
        # Run command in working directory
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=env.working_dir
        )
        
        return process
        
    except Exception as e:
        raise ValueError(f"Failed to run command: {e}")


async def auto_run_tests(env: Environment) -> Dict[str, any]:
    """Auto-detect and run tests."""
    manager = env.config.manager.value
    
    try:
        if manager == "node":
            # Check for package.json
            if not (Path(env.working_dir) / "package.json").exists():
                return {"error": "No package.json found"}

            # Run npm/yarn test
            process = await run_command(env.id, "npm test")
            stdout, stderr = await process.communicate()
            
            return {
                "success": process.returncode == 0,
                "output": stdout.decode() if stdout else "",
                "error": stderr.decode() if stderr else ""
            }

        elif manager == "bun":
            # Similar to node but use bun test
            process = await run_command(env.id, "bun test")
            stdout, stderr = await process.communicate()
            
            return {
                "success": process.returncode == 0,
                "output": stdout.decode() if stdout else "",
                "error": stderr.decode() if stderr else ""
            }

        elif manager == "uv":
            # Check for pyproject.toml
            if not (Path(env.working_dir) / "pyproject.toml").exists():
                return {"error": "No pyproject.toml found"}

            # Run pytest
            process = await run_command(env.id, "uv run pytest")
            stdout, stderr = await process.communicate()
            
            return {
                "success": process.returncode == 0,
                "output": stdout.decode() if stdout else "",
                "error": stderr.decode() if stderr else ""
            }

        else:
            raise ValueError(f"Unsupported manager: {manager}")

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }