"""Environment management and lifecycle."""
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, cast

from mcp_runtime_server.types import Runtime, Environment
from mcp_runtime_server.environments.runtime import detect_runtime, setup_runtime_env
from mcp_runtime_server.environments.sandbox import create_sandbox, cleanup_sandbox
from mcp_runtime_server.git import clone_repository
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)

async def create_environment(github_url: str, branch: Optional[str] = None) -> Environment:
    """Create new sandboxed environment."""
    try:
        env_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        
        # Create root temp directory for sandbox
        temp_dir = Path(tempfile.mkdtemp(prefix=f"mcp-{env_id}-"))
        
        # Create sandbox within temp directory
        sandbox_info = create_sandbox(temp_dir)
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
            env_vars=env_vars
        )

    except Exception as e:
        logger.error({
            "event": "environment_creation_failed",
            "error": str(e)
        })
        if "temp_dir" in locals():
            cleanup_sandbox(cast(Path, temp_dir))
        raise RuntimeError(f"Failed to create environment: {e}")

def cleanup_environment(env: Environment) -> None:
    """Clean up environment."""
    try:
        # The work_dir's parent is our sandbox root temp directory
        cleanup_sandbox(env.work_dir.parent)
    except Exception as e:
        logger.error({
            "event": "environment_cleanup_failed", 
            "error": str(e)
        })