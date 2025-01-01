"""Environment management and lifecycle."""
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from mcp_runtime_server.types import Runtime, Runtimes, RuntimeSignature, Environment, EnvironmentConfig
from mcp_runtime_server.environments.runtime import detect_runtime, setup_runtime_env
from mcp_runtime_server.environments.sandbox import create_sandbox, cleanup_sandbox
from mcp_runtime_server.environments.commands import clone_repository
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)

async def create_environment(base_dir: Path, github_url: str, branch: Optional[str] = None) -> Environment:
    """Create new sandboxed environment."""
    try:
        env_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        sandbox_info = create_sandbox(base_dir, env_id)
        env_vars = sandbox_info.env_vars
        
        await clone_repository(github_url, sandbox_info.work_dir, branch, env_vars)
        runtime = detect_runtime(sandbox_info.work_dir)
        
        env_vars = setup_runtime_env(
            env_vars,
            runtime=runtime,
            work_dir=sandbox_info.work_dir
        )
        
        return Environment(
            id=env_id,
            config=EnvironmentConfig(github_url=github_url),
            runtime=runtime,
            work_dir=sandbox_info.work_dir,
            created_at=datetime.now(timezone.utc),
            sandbox_root=sandbox_info.root,
            bin_dir=sandbox_info.bin_dir,
            env_vars=env_vars,
            root_dir=sandbox_info.root,
            _temp_dir=None
        )

    except Exception as e:
        logger.error({
            "event": "environment_creation_failed",
            "error": str(e)
        })
        raise RuntimeError(f"Failed to create environment: {e}")

def cleanup_environment(env: Environment) -> None:
    """Clean up environment."""
    try:
        cleanup_sandbox(env.sandbox_root)
    except Exception as e:
        logger.error({
            "event": "environment_cleanup_failed", 
            "error": str(e)
        })
