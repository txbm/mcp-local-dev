"""Runtime environment management."""
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict

from mcp_runtime_server.sandbox.environment import create_sandbox, cleanup_sandbox
from mcp_runtime_server.types import RuntimeConfig, Environment

logger = logging.getLogger(__name__)

# Active environments
ENVIRONMENTS: Dict[str, Environment] = {}


async def create_environment(config: RuntimeConfig) -> Environment:
    """Create a new runtime environment."""
    try:
        # Create unique environment ID
        env_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

        # Create sandbox first
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
            id=env_id,
            config=config,
            created_at=datetime.utcnow(),
            working_dir=str(work_dir)
        )
        
        ENVIRONMENTS[env.id] = env
        return env
        
    except Exception as e:
        if 'sandbox' in locals():
            cleanup_sandbox(sandbox)
        raise ValueError(f"Failed to create environment: {e}") from e


async def cleanup_environment(env_id: str) -> None:
    """Clean up a runtime environment."""
    if env_id not in ENVIRONMENTS:
        return
        
    env = ENVIRONMENTS[env_id]
    work_dir = Path(env.working_dir)
    sandbox_root = work_dir.parent.parent  # Get sandbox root from work dir
    
    try:
        # Find and clean up the sandbox
        sandbox = next(
            sb for sb in get_active_sandboxes()
            if sb.root == sandbox_root
        )
        cleanup_sandbox(sandbox)
            
    finally:
        del ENVIRONMENTS[env_id]


async def run_command(env_id: str, command: str) -> asyncio.subprocess.Process:
    """Run a command in an environment."""
    if env_id not in ENVIRONMENTS:
        raise ValueError(f"Unknown environment: {env_id}")
        
    env = ENVIRONMENTS[env_id]
    work_dir = Path(env.working_dir)
    sandbox_root = work_dir.parent.parent
    
    try:
        # Find associated sandbox
        sandbox = next(
            sb for sb in get_active_sandboxes()
            if sb.root == sandbox_root
        )
        
        # Run command in sandbox environment
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=env.working_dir,
            env=sandbox.env_vars
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

            # Create and activate virtual environment
            venv_process = await run_command(env.id, "uv venv")
            stdout, stderr = await venv_process.communicate()
            if venv_process.returncode != 0:
                return {
                    "success": False,
                    "error": f"Failed to create virtual environment: {stderr.decode()}"
                }

            # Install dependencies
            install_process = await run_command(env.id, "uv pip install -e .")
            stdout, stderr = await install_process.communicate()
            if install_process.returncode != 0:
                return {
                    "success": False,
                    "error": f"Failed to install dependencies: {stderr.decode()}"
                }

            # Install pytest
            pytest_install = await run_command(env.id, "uv pip install pytest")
            stdout, stderr = await pytest_install.communicate()
            if pytest_install.returncode != 0:
                return {
                    "success": False,
                    "error": f"Failed to install pytest: {stderr.decode()}"
                }

            # Run pytest
            process = await run_command(env.id, "python -m pytest")
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