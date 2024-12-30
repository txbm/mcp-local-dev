"""Runtime environment management."""
import asyncio
import logging
import os
import shutil
import appdirs
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from mcp_runtime_server.sandbox.security import apply_restrictions, remove_restrictions
from mcp_runtime_server.types import RuntimeConfig, Environment

logger = logging.getLogger(__name__)

# Active environments
ENVIRONMENTS: Dict[str, Environment] = {}


def _create_dir_structure(root: Path) -> Dict[str, Path]:
    """Create environment directory structure."""
    dirs = {
        "bin": root / "bin",
        "tmp": root / "tmp",
        "work": root / "work"
    }
    
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
        
    return dirs


def _prepare_env_vars(dirs: Dict[str, Path]) -> Dict[str, str]:
    """Prepare environment variables."""
    env = os.environ.copy()
    
    # Set up basic environment
    env.update({
        "HOME": str(dirs["work"]),
        "TMPDIR": str(dirs["tmp"]),
        "PATH": f"{dirs['bin']}:{env.get('PATH', '')}"
    })
    
    # Remove potentially dangerous variables
    for var in ["PYTHONPATH", "NODE_PATH", "LD_PRELOAD", "LD_LIBRARY_PATH"]:
        env.pop(var, None)
        
    return env


async def create_environment(config: RuntimeConfig) -> Environment:
    """Create a new runtime environment."""
    try:
        # Create unique environment ID and root directory
        env_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        root_dir = Path(appdirs.user_cache_dir("mcp-runtime-server")) / "envs" / env_id
        
        # Create directories
        dirs = _create_dir_structure(root_dir)
        env_vars = _prepare_env_vars(dirs)
        
        # Apply security restrictions
        apply_restrictions(root_dir)
        
        # Create environment instance
        env = Environment(
            id=env_id,
            config=config,
            created_at=datetime.utcnow(),
            root_dir=root_dir,
            bin_dir=dirs["bin"],
            work_dir=dirs["work"],
            tmp_dir=dirs["tmp"],
            env_vars=env_vars
        )
        
        # Clone repository
        process = await asyncio.create_subprocess_exec(
            "git", "clone", config.github_url, str(env.work_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env.env_vars
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise ValueError(f"Failed to clone repository: {stderr.decode()}")

        ENVIRONMENTS[env.id] = env
        return env
        
    except Exception as e:
        if 'root_dir' in locals() and root_dir.exists():
            remove_restrictions(root_dir)
            shutil.rmtree(root_dir)
        raise ValueError(f"Failed to create environment: {e}") from e


async def cleanup_environment(env_id: str) -> None:
    """Clean up a runtime environment."""
    if env_id not in ENVIRONMENTS:
        return
        
    env = ENVIRONMENTS[env_id]
    try:
        remove_restrictions(env.root_dir)
        if env.root_dir.exists():
            shutil.rmtree(env.root_dir)
    finally:
        del ENVIRONMENTS[env_id]


async def run_command(env_id: str, command: str) -> asyncio.subprocess.Process:
    """Run a command in an environment."""
    if env_id not in ENVIRONMENTS:
        raise ValueError(f"Unknown environment: {env_id}")
        
    env = ENVIRONMENTS[env_id]
    
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=env.work_dir,
            env=env.env_vars
        )
        
        return process
        
    except Exception as e:
        raise ValueError(f"Failed to run command: {e}")


async def auto_run_tests(env: Environment) -> Dict[str, any]:
    """Auto-detect and run tests."""
    try:
        if not (env.work_dir / "pyproject.toml").exists():
            return {"error": "No pyproject.toml found"}

        # Create venv and install deps
        cmds = [
            "uv venv",
            "uv pip install -e .",
            "uv pip install pytest",
            "python -m pytest"
        ]
        
        for cmd in cmds:
            process = await run_command(env.id, cmd)
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                return {
                    "success": False,
                    "error": f"Command '{cmd}' failed: {stderr.decode()}"
                }
        
        return {
            "success": True,
            "output": stdout.decode() if stdout else ""
        }

    except Exception as e:
        return {"success": False, "error": str(e)}