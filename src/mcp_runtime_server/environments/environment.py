"""Environment lifecycle management."""

import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fuuid import b58_fuuid

from mcp_runtime_server.types import Environment
from mcp_runtime_server.runtimes.runtime import (
    detect_runtime,
    make_runtime_env,
    RUNTIME_CONFIGS,
)
from mcp_runtime_server.runtimes.binaries import ensure_binary
from mcp_runtime_server.environments.sandbox import create_sandbox, cleanup_sandbox
from mcp_runtime_server.environments.commands import clone_repository, run_install
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


async def create_environment(
    github_url: str, branch: Optional[str] = None
) -> Environment:
    """Create new sandboxed environment.

    Args:
        github_url: GitHub repository URL
        branch: Optional branch to clone

    Returns:
        Environment instance

    Raises:
        RuntimeError: If environment creation fails at any stage
    """

    env_id = b58_fuuid()
    logger.info(
        {
            "event": "creating_environment",
            "env_id": env_id,
            "github_url": github_url,
            "branch": branch,
        }
    )
    sandbox = create_sandbox(f"mcp-{env_id}")

    logger.debug({"event": "cloning_repository", "work_dir": str(sandbox.work_dir)})
    await clone_repository(github_url, sandbox.work_dir, branch, sandbox.env_vars)

    runtime = detect_runtime(sandbox.work_dir)
    logger.info(
        {"event": "runtime_detected", "env_id": env_id, "runtime": runtime.value}
    )

    env_vars = make_runtime_env(runtime, sandbox.work_dir, sandbox.env_vars)

    env = Environment(
        id=env_id,
        runtime=runtime,
        sandbox=sandbox,
        created_at=datetime.now(timezone.utc),
        env_vars=env_vars,
    )

    logger.debug(
        {
            "event": "ensuring_runtime_binary",
            "env_id": env_id,
            "runtime": runtime.value,
        }
    )
    config = RUNTIME_CONFIGS[runtime]
    binary_path = await ensure_binary(runtime, config)
    target_path = env.sandbox.bin_dir / binary_path.name
    shutil.copy2(binary_path, target_path)
    target_path.chmod(0o755)

    logger.debug(
        {
            "event": "installing_dependencies",
            "env_id": env_id,
            "runtime": runtime.value,
        }
    )
    await run_install(env)

    logger.info(
        {
            "event": "environment_ready",
            "env_id": env_id,
            "runtime": runtime.value,
            "work_dir": str(sandbox.work_dir),
        }
    )

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
    try:
        logger.debug({"event": "cleaning_environment", "env_id": env.id})

        cleanup_sandbox(env.sandbox)
        env.tempdir.cleanup()

        logger.info({"event": "environment_cleaned", "env_id": env.id})

    except Exception as e:
        logger.error(
            {"event": "environment_cleanup_failed", "env_id": env.id, "error": str(e)}
        )
        raise RuntimeError(f"Failed to cleanup environment: {e}")
