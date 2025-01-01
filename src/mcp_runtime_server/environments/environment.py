"""Environment management and lifecycle."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fuuid import b58_fuuid

from mcp_runtime_server.types import Environment
from mcp_runtime_server.environments.runtime import detect_runtime, setup_runtime_env
from mcp_runtime_server.environments.sandbox import create_sandbox, cleanup_sandbox
from mcp_runtime_server.environments.commands import clone_repository
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


async def create_environment(
    github_url: str, branch: Optional[str] = None
) -> Environment:
    """Create new sandboxed environment."""
    try:
        env_id = b58_fuuid()

        # Create temp directory that will be automatically cleaned up
        temp_dir = tempfile.TemporaryDirectory(prefix=f"mcp-{env_id}-")
        sandbox = create_sandbox(Path(temp_dir.name))
        env_vars = sandbox.env_vars

        # Clone and detect runtime
        await clone_repository(github_url, sandbox.work_dir, branch, env_vars)
        runtime = detect_runtime(sandbox.work_dir)

        # Setup runtime environment
        env_vars = setup_runtime_env(
            env_vars, runtime=runtime, work_dir=sandbox.work_dir
        )

        return Environment(
            id=env_id,
            runtime=runtime,
            sandbox=sandbox,
            work_dir=sandbox.work_dir,
            created_at=datetime.now(timezone.utc),
            env_vars=env_vars,
            tempdir=temp_dir,  # Store reference to keep directory alive
        )

    except Exception as e:
        logger.error({"event": "environment_creation_failed", "error": str(e)})
        if "temp_dir" in locals():
            temp_dir.cleanup()
        raise RuntimeError(f"Failed to create environment: {e}")


def cleanup_environment(env: Environment) -> None:
    """Clean up environment.

    This performs an explicit cleanup of the sandbox environment and its resources.
    Even if this is not called, the environment will be cleaned up when the Environment
    object is destroyed via the TemporaryDirectory.
    """
    try:
        # First try sandbox cleanup for proper resource cleanup
        cleanup_sandbox(env.sandbox)
        # Then cleanup temporary directory
        env.tempdir.cleanup()

    except Exception as e:
        logger.error({"event": "environment_cleanup_failed", "error": str(e)})
        # Re-raise so caller knows about failure
        raise RuntimeError(f"Failed to cleanup environment: {e}")
