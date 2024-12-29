"""Runtime environment management."""
import os
import asyncio
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from mcp_runtime_server.types import RuntimeConfig, RuntimeEnv, CaptureConfig
from mcp_runtime_server.sandbox import create_sandbox, cleanup_sandbox
from mcp_runtime_server.binaries import ensure_binary
from mcp_runtime_server.binaries.constants import RUNTIME_BINARIES


# Active environments
ACTIVE_ENVS: Dict[str, RuntimeEnv] = {}


async def create_environment(config: RuntimeConfig) -> RuntimeEnv:
    """Create a new runtime environment.
    
    Args:
        config: Runtime configuration
        
    Returns:
        RuntimeEnv instance
        
    Raises:
        RuntimeError: If environment creation fails
    """
    # Create sandbox environment
    sandbox = create_sandbox(base_env=config.env)
    
    try:
        # Get binary manager
        binary_path = await ensure_binary(config.manager.value)
        
        # Link binary into sandbox
        binary_name = binary_path.name
        dest = sandbox.bin_dir / binary_name
        dest.write_bytes(binary_path.read_bytes())
        dest.chmod(0o755)
        
        # Create environment
        env = RuntimeEnv(
            id=sandbox.id,
            config=config,
            created_at=datetime.utcnow(),
            working_dir=str(sandbox.root),
            env_vars=sandbox.env_vars
        )
        
        ACTIVE_ENVS[env.id] = env
        return env
        
    except Exception as e:
        cleanup_sandbox(sandbox)
        raise RuntimeError(f"Failed to create environment: {e}") from e


async def cleanup_environment(env_id: str, force: bool = False) -> None:
    """Clean up a runtime environment.
    
    Args:
        env_id: Environment identifier
        force: Force cleanup even if processes are running
    """
    if env_id not in ACTIVE_ENVS:
        return
        
    env = ACTIVE_ENVS[env_id]
    
    try:
        # Clean up sandbox
        sandbox_info = create_sandbox.__new__(create_sandbox)
        sandbox_info.id = env_id
        sandbox_info.root = Path(env.working_dir)
        cleanup_sandbox(sandbox_info)
        
    finally:
        del ACTIVE_ENVS[env_id]


async def run_in_env(
    env_id: str,
    command: str,
    capture_config: Optional[CaptureConfig] = None
) -> asyncio.subprocess.Process:
    """Run a command in an environment.
    
    Args:
        env_id: Environment identifier
        command: Command to run
        capture_config: Output capture configuration
        
    Returns:
        Process object
        
    Raises:
        RuntimeError: If command execution fails
    """
    if env_id not in ACTIVE_ENVS:
        raise RuntimeError(f"Environment {env_id} not found")
        
    env = ACTIVE_ENVS[env_id]
    
    # Set up output capture
    stdout = asyncio.subprocess.PIPE if capture_config else None
    stderr = asyncio.subprocess.PIPE if capture_config else None
    
    try:
        # Run in sandbox
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=stdout,
            stderr=stderr,
            cwd=env.working_dir,
            env=env.env_vars
        )
        
        return process
        
    except Exception as e:
        raise RuntimeError(f"Failed to run command: {e}") from e