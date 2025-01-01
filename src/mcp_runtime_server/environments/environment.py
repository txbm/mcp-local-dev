"""Environment management and lifecycle."""
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from mcp_runtime_server.types import Runtime, Environment
from mcp_runtime_server.environments.runtime import detect_runtime, setup_runtime_env
from mcp_runtime_server.environments.sandbox import create_sandbox
from mcp_runtime_server.git import clone_repository
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)

async def create_environment(github_url: str, branch: Optional[str] = None) -> Environment:
    """Create new sandboxed environment."""
    try:
        env_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        
        # Create temp directory that will be automatically cleaned up
        temp_dir = tempfile.TemporaryDirectory(prefix=f"mcp-{env_id}-")
        sandbox_info = create_sandbox(Path(temp_dir.name))
        env_vars = sandbox_info.env_vars
        
        # Clone and detect runtime
        await clone_repository(github_url, sandbox_info.work_dir, branch, env_vars)
        runtime = detect_runtime(sandbox_info.work_dir)
        
        # Setup runtime environment
        env_vars = setup_runtime_env(
            env_vars,
            runtime=runtime,
            work_dir=sandbox_info.work_dir
        )
        
        return Environment(
            id=env_id,
            runtime=runtime,
            work_dir=sandbox_info.work_dir,
            created_at=datetime.now(timezone.utc),
            env_vars=env_vars,
            _tempdir=temp_dir  # Store reference to keep directory alive
        )

    except Exception as e:
        logger.error({
            "event": "environment_creation_failed",
            "error": str(e)
        })
        raise RuntimeError(f"Failed to create environment: {e}")