"""Environment lifecycle management."""

import os
from pathlib import Path
import shutil
from datetime import datetime, timezone
from typing import Optional

from fuuid import b58_fuuid

from mcp_local_dev.types import Environment, Sandbox
from mcp_local_dev.runtimes.runtime import detect_runtime, install_runtime
from mcp_local_dev.sandboxes.sandbox import (
    create_sandbox,
    cleanup_sandbox,
)
from mcp_local_dev.sandboxes.git import clone_github_repository
from mcp_local_dev.logging import get_logger

logger = get_logger(__name__)


async def create_environment_from_github(
    staging: Sandbox, github_url: str, branch: Optional[str] = None
) -> Environment:
    repo = await clone_github_repository(staging, github_url, branch)
    env = await create_environment(repo)
    cleanup_sandbox(staging)
    return env


async def create_environment(path: Path) -> Environment:
    """Create new environment from filesystem path."""
    env_id = b58_fuuid()
    sandbox = await create_sandbox(f"mcp-{env_id}-")

    shutil.copytree(path, sandbox.work_dir, dirs_exist_ok=True)
    os.chmod(sandbox.work_dir, 0o700)
    os.chmod(sandbox.bin_dir, 0o700)

    runtime_config = detect_runtime(sandbox)
    await install_runtime(sandbox, runtime_config)

    return Environment(
        id=env_id,
        runtime_config=runtime_config,
        sandbox=sandbox,
        created_at=datetime.now(timezone.utc),
    )


def cleanup_environment(env: Environment) -> None:
    """Clean up environment and its resources."""

    cleanup_sandbox(env.sandbox)
