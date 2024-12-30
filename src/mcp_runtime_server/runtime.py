"""Runtime environment management."""
import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any

from mcp_runtime_server.types import (
    RuntimeConfig, 
    Environment,
    CaptureConfig
)
from mcp_runtime_server.sandbox import create_sandbox, cleanup_sandbox
from mcp_runtime_server.binaries import ensure_binary
from mcp_runtime_server.errors import log_error, EnvironmentError

logger = logging.getLogger(__name__)

# Active environments
ENVIRONMENTS: Dict[str, Environment] = {}


async def create_environment(config: RuntimeConfig) -> Environment:
    """Create a new runtime environment.
    
    Args:
        config: Runtime configuration
        
    Returns:
        Environment instance
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
        env = Environment(
            id=sandbox.id,
            config=config,
            created_at=datetime.utcnow(),
            working_dir=str(sandbox.root),
            env_vars=sandbox.env_vars
        )
        
        ENVIRONMENTS[env.id] = env
        return env
        
    except Exception as e:
        cleanup_sandbox(sandbox)
        context = {"config": config.dict()} if hasattr(config, "dict") else {"config": str(config)}
        log_error(e, context, logger)
        raise RuntimeError(f"Failed to create environment: {e}") from e


async def cleanup_environment(env_id: str, force: bool = False) -> None:
    """Clean up a runtime environment.
    
    Args:
        env_id: Environment identifier
        force: Force cleanup even if processes are running
    """
    if env_id not in ENVIRONMENTS:
        return
        
    env = ENVIRONMENTS[env_id]
    
    try:
        # Clean up sandbox
        sandbox_info = create_sandbox.__new__(create_sandbox)
        sandbox_info.id = env_id
        sandbox_info.root = Path(env.working_dir)
        cleanup_sandbox(sandbox_info)
        
    except Exception as e:
        context = {"env_id": env_id, "force": force}
        log_error(e, context, logger)
        raise
        
    finally:
        del ENVIRONMENTS[env_id]


async def run_command(
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
    """
    if env_id not in ENVIRONMENTS:
        raise EnvironmentError(env_id)
        
    env = ENVIRONMENTS[env_id]
    
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
        context = {"env_id": env_id, "command": command}
        log_error(e, context, logger)
        raise RuntimeError(f"Failed to run command: {e}") from e