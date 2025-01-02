"""Environment lifecycle management."""

from pathlib import Path
import shutil
from datetime import datetime, timezone
from typing import Optional

from fuuid import b58_fuuid

from mcp_runtime_server.types import Environment, Sandbox
from mcp_runtime_server.runtimes.runtime import (
    detect_runtime,
)
from mcp_runtime_server.sandboxes.sandbox import create_sandbox, cleanup_sandbox
from mcp_runtime_server.sandboxes.git import clone_github_repository
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


async def create_environment_from_github(
    staging: Sandbox, github_url: str, branch: Optional[str] = None
) -> Environment:

    repo = await clone_github_repository(staging, github_url, branch)
    env = await create_environment(repo)

    return env


async def create_environment(path: Path) -> Environment:
    """Create new environment from a filesystem path."""

    env_id = b58_fuuid()
    logger.info(
        {
            "event": "creating_environment",
            "env_id": env_id,
            "path": path,
        }
    )
    sandbox = await create_sandbox(f"mcp-{env_id}-")
    shutil.copytree(path, sandbox.work_dir, dirs_exist_ok=True)

    runtime_config = detect_runtime(sandbox)
    logger.info(
        {
            "event": "runtime_detected",
            "env_id": env_id,
            "runtime": runtime_config.name.value,
        }
    )

    env = Environment(
        id=env_id,
        runtime_config=runtime_config,
        sandbox=sandbox,
        created_at=datetime.now(timezone.utc),
    )

    # config = RUNTIME_CONFIGS[runtime]
    # binary_path = await ensure_binary(runtime, config)
    # target_path = env.sandbox.bin_dir / binary_path.name
    # shutil.copy2(binary_path, target_path)
    # target_path.chmod(0o755)

    # logger.debug(
    #     {
    #         "event": "installing_dependencies",
    #         "env_id": env_id,
    #         "runtime": runtime.value,
    #     }
    # )
    # await run_install(env)

    # logger.info(
    #     {
    #         "event": "environment_ready",
    #         "env_id": env_id,
    #         "runtime": runtime.value,
    #         "work_dir": str(sandbox.work_dir),
    #     }
    # )

    return env


def cleanup_environment(env: Environment) -> None:
    """Clean up environment and its resources.

    Even if not called, environment will be cleaned up when Environment
    object is destroyed via TemporaryDirectory.

    Args:
        env: Environment instance to clean up

    Raises:
        RuntimeError: If cleanup fails
    """
    logger.debug({"event": "cleaning_environment", "env_id": env.id})

    cleanup_sandbox(env.sandbox)

    logger.info({"event": "environment_cleaned", "env_id": env.id})
