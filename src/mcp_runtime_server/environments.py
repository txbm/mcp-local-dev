"""Environment management."""

import logging
import os
import shutil
import appdirs
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from mcp_runtime_server.types import EnvironmentConfig, Environment
from mcp_runtime_server.detection import detect_runtime
from mcp_runtime_server.git import clone_repository

logger = logging.getLogger(__name__)

ENVIRONMENTS: Dict[str, Environment] = {}


async def create_environment(config: EnvironmentConfig) -> Environment:
    """Create a new runtime environment."""
    try:
        env_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        root_dir = Path(appdirs.user_cache_dir("mcp-runtime-server")) / "envs" / env_id

        bin_dir = root_dir / "bin"
        tmp_dir = root_dir / "tmp"
        work_dir = root_dir / "work"

        for d in [bin_dir, tmp_dir, work_dir]:
            d.mkdir(parents=True, exist_ok=True)

        env_vars = os.environ.copy()
        env_vars.update(
            {
                "HOME": str(work_dir),
                "TMPDIR": str(tmp_dir),
                "PATH": f"{bin_dir}:{env_vars.get('PATH', '')}",
            }
        )

        for var in ["PYTHONPATH", "NODE_PATH", "LD_PRELOAD", "LD_LIBRARY_PATH"]:
            env_vars.pop(var, None)

        env = Environment(
            id=env_id,
            config=config,
            created_at=datetime.now(timezone.utc),
            root_dir=root_dir,
            bin_dir=bin_dir,
            work_dir=work_dir,
            tmp_dir=tmp_dir,
            manager=None,
            env_vars=env_vars,
        )

        await clone_repository(config.github_url, str(work_dir), env_vars)

        runtime = detect_runtime(str(work_dir))
        if not runtime:
            raise RuntimeError("Unable to detect runtime for repository")

        env.manager = runtime.manager
        env.env_vars.update(runtime.env_vars)

        ENVIRONMENTS[env.id] = env
        return env

    except Exception as e:
        if "root_dir" in locals() and root_dir.exists():
            shutil.rmtree(str(root_dir))
        raise RuntimeError(f"Failed to create environment: {e}") from e


def cleanup_environment(env_id: str) -> None:
    """Clean up a runtime environment."""
    if env_id not in ENVIRONMENTS:
        return

    env = ENVIRONMENTS[env_id]
    try:
        if env.root_dir.exists():
            shutil.rmtree(str(env.root_dir))
            logger.debug(f"removed {env.root_dir}")
    finally:
        del ENVIRONMENTS[env_id]
