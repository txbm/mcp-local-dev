"""Environment lifecycle management."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fuuid import b58_fuuid

from mcp_runtime_server.types import Environment, Runtime
from mcp_runtime_server.environments.runtime import detect_runtime, make_runtime_env, RUNTIME_CONFIGS
from mcp_runtime_server.environments.sandbox import create_sandbox, cleanup_sandbox
from mcp_runtime_server.environments.commands import clone_repository, run_install
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


async def create_environment(github_url: str, branch: Optional[str] = None) -> Environment:
    """Create new sandboxed environment.
    
    Args:
        github_url: GitHub repository URL
        branch: Optional branch to clone
        
    Returns:
        Environment instance
        
    Raises:
        RuntimeError: If environment creation fails at any stage
    """
    env_id = None
    temp_dir = None
    
    try:
        # Generate unique ID
        env_id = b58_fuuid()
        logger.info({
            "event": "creating_environment",
            "env_id": env_id,
            "github_url": github_url,
            "branch": branch
        })

        # Create temp directory that will be automatically cleaned up
        temp_dir = tempfile.TemporaryDirectory(prefix=f"mcp-{env_id}-")
        sandbox = create_sandbox(Path(temp_dir.name))
        
        # Clone repository
        logger.debug({
            "event": "cloning_repository",
            "work_dir": str(sandbox.work_dir)
        })
        await clone_repository(github_url, sandbox.work_dir, branch, sandbox.env_vars)

        # Detect runtime type
        runtime = detect_runtime(sandbox.work_dir)
        logger.info({
            "event": "runtime_detected",
            "env_id": env_id,
            "runtime": runtime.value
        })

        # Set up runtime environment
        env_vars = make_runtime_env(runtime, sandbox.work_dir, sandbox.env_vars)

        # Create environment instance
        env = Environment(
            id=env_id,
            runtime=runtime,
            sandbox=sandbox,
            created_at=datetime.now(timezone.utc),
            env_vars=env_vars,
            tempdir=temp_dir
        )

        # Install runtime dependencies
        logger.debug({
            "event": "installing_dependencies",
            "env_id": env_id,
            "runtime": runtime.value
        })
        await run_install(env)
        
        logger.info({
            "event": "environment_ready",
            "env_id": env_id,
            "runtime": runtime.value,
            "work_dir": str(sandbox.work_dir)
        })

        return env

    except Exception as e:
        logger.error({
            "event": "environment_creation_failed",
            "env_id": env_id,
            "error": str(e)
        })
        
        # Clean up temp directory if it was created
        if temp_dir:
            logger.debug({
                "event": "cleaning_failed_environment",
                "env_id": env_id
            })
            temp_dir.cleanup()
            
        raise RuntimeError(f"Failed to create environment: {e}")


def cleanup_environment(env: Environment) -> None:
    """Clean up environment and its resources.
    
    This performs an explicit cleanup of the sandbox environment and its resources.
    Even if this is not called, the environment will be cleaned up when the Environment
    object is destroyed via the TemporaryDirectory.
    
    Args:
        env: Environment instance to clean up
        
    Raises:
        RuntimeError: If cleanup fails
    """
    try:
        logger.debug({
            "event": "cleaning_environment",
            "env_id": env.id
        })
        
        # First try sandbox cleanup for proper resource cleanup
        cleanup_sandbox(env.sandbox)
        
        # Then cleanup temporary directory
        env.tempdir.cleanup()
        
        logger.info({
            "event": "environment_cleaned",
            "env_id": env.id
        })

    except Exception as e:
        logger.error({
            "event": "environment_cleanup_failed",
            "env_id": env.id,
            "error": str(e)
        })
        raise RuntimeError(f"Failed to cleanup environment: {e}")