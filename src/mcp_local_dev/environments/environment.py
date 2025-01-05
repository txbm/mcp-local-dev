"""Environment lifecycle management."""
import os
from pathlib import Path
import shutil
import json
from datetime import datetime, timezone
from typing import Optional, Dict

from fuuid import b58_fuuid
import mcp.types as mcp_types

from mcp_local_dev.types import Environment, Sandbox, Runtime
from mcp_local_dev.runtimes.runtime import detect_runtime, install_runtime
from mcp_local_dev.sandboxes.sandbox import (
    create_sandbox,
    cleanup_sandbox,
)
from mcp_local_dev.sandboxes.git import clone_github_repository
from mcp_local_dev.test_runners.execution import auto_run_tests
from mcp_local_dev.logging import get_logger

logger = get_logger(__name__)

# In-memory environment store
_ENVIRONMENTS: Dict[str, Environment] = {}

async def create_environment_from_github(github_url: str, branch: Optional[str] = None) -> Environment:
    """Create new environment from GitHub repository."""
    staging = await create_sandbox("mcp-staging-")
    try:
        repo = await clone_github_repository(staging, github_url, branch)
        env = await create_environment_from_path(repo)
        return env
    finally:
        cleanup_sandbox(staging)

async def create_environment_from_path(path: Path) -> Environment:
    """Create new environment from filesystem path."""
    env_id = b58_fuuid()
    sandbox = await create_sandbox(f"mcp-{env_id}-")

    shutil.copytree(path, sandbox.work_dir, dirs_exist_ok=True)
    os.chmod(sandbox.work_dir, 0o700)
    os.chmod(sandbox.bin_dir, 0o700)

    runtime_config = detect_runtime(sandbox)
    await install_runtime(sandbox, runtime_config)

    env = Environment(
        id=env_id,
        runtime_config=runtime_config,
        sandbox=sandbox,
        created_at=datetime.now(timezone.utc),
    )
    
    _ENVIRONMENTS[env_id] = env
    return env

async def run_environment_tests(env: Environment) -> list[mcp_types.TextContent]:
    """Run tests in environment."""
    try:
        test_results = await auto_run_tests(env)
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "data": test_results
            })
        )]
    except Exception as e:
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e)
            })
        )]

def get_environment(env_id: str) -> Optional[Environment]:
    """Get environment by ID."""
    return _ENVIRONMENTS.get(env_id)

def cleanup_environment(env: Environment) -> None:
    """Clean up environment and its resources."""
    if env.id in _ENVIRONMENTS:
        del _ENVIRONMENTS[env.id]
    cleanup_sandbox(env.sandbox)
