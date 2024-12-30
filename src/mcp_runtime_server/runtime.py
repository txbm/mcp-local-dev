"""Runtime environment management."""
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from mcp_runtime_server.sandbox.environment import create_sandbox, cleanup_sandbox
from mcp_runtime_server.types import RuntimeConfig, Environment

logger = logging.getLogger(__name__)

# Active runtime state
RUNTIME_STATE: Dict[str, Any] = {}


async def create_environment(config: RuntimeConfig) -> Environment:
    """Create a new runtime environment."""
    try:
        # Create sandbox and environment
        sandbox = create_sandbox()
        work_dir = sandbox.root / "work"
        
        # Clone repository
        process = await asyncio.create_subprocess_exec(
            "git", "clone", config.github_url, str(work_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=sandbox.env_vars
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise ValueError(f"Failed to clone repository: {stderr.decode()}")

        # Create environment
        env = Environment(
            id=datetime.utcnow().strftime("%Y%m%d-%H%M%S"),
            config=config,
            created_at=datetime.utcnow(),
            working_dir=str(work_dir)
        )
        
        # Store complete runtime state
        RUNTIME_STATE[env.id] = {
            "env": env,
            "sandbox": sandbox
        }
        
        return env
        
    except Exception as e:
        if 'sandbox' in locals():
            cleanup_sandbox(sandbox)
        raise ValueError(f"Failed to create environment: {e}") from e


async def cleanup_environment(env_id: str) -> None:
    """Clean up a runtime environment."""
    if env_id not in RUNTIME_STATE:
        return
        
    state = RUNTIME_STATE[env_id]
    try:
        cleanup_sandbox(state["sandbox"])
    finally:
        del RUNTIME_STATE[env_id]


async def run_command(env_id: str, command: str) -> asyncio.subprocess.Process:
    """Run a command in an environment."""
    if env_id not in RUNTIME_STATE:
        raise ValueError(f"Unknown environment: {env_id}")
        
    state = RUNTIME_STATE[env_id]
    
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=state["env"].working_dir,
            env=state["sandbox"].env_vars
        )
        
        return process
        
    except Exception as e:
        raise ValueError(f"Failed to run command: {e}")


async def auto_run_tests(env: Environment) -> Dict[str, any]:
    """Auto-detect and run tests."""
    manager = env.config.manager.value
    
    try:
        if not Path(env.working_dir, "pyproject.toml").exists():
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