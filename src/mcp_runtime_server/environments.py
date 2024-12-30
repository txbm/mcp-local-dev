"""Environment management."""
import asyncio
import logging
import os
import shutil
import appdirs
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from mcp_runtime_server.types import RuntimeConfig, Environment
from mcp_runtime_server.commands import run_command

logger = logging.getLogger(__name__)

ENVIRONMENTS: Dict[str, Environment] = {}

async def create_environment(config: RuntimeConfig) -> Environment:
    """Create a new runtime environment."""
    try:
        env_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        root_dir = Path(appdirs.user_cache_dir("mcp-runtime-server")) / "envs" / env_id
        
        bin_dir = root_dir / "bin"
        tmp_dir = root_dir / "tmp"
        work_dir = root_dir / "work"
        
        for d in [bin_dir, tmp_dir, work_dir]:
            d.mkdir(parents=True)
        
        env_vars = os.environ.copy()
        env_vars.update({
            "HOME": str(work_dir),
            "TMPDIR": str(tmp_dir),
            "PATH": f"{bin_dir}:{env_vars.get('PATH', '')}"
        })
        
        for var in ["PYTHONPATH", "NODE_PATH", "LD_PRELOAD", "LD_LIBRARY_PATH"]:
            env_vars.pop(var, None)
            
        env = Environment(
            id=env_id,
            config=config,
            created_at=datetime.utcnow(),
            root_dir=root_dir,
            bin_dir=bin_dir,
            work_dir=work_dir,
            tmp_dir=tmp_dir,
            env_vars=env_vars
        )
        
        # Use explicit protocol override for public repos
        clone_url = f"//:https://github.com{config.github_url.split('github.com')[1].strip('/')}".replace(".git", "")
        
        process = await run_command(
            f"git clone {clone_url} {work_dir}",
            str(work_dir.parent),
            env_vars
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"Failed to clone repository: {stderr.decode()}")
            
        ENVIRONMENTS[env.id] = env
        return env
        
    except Exception as e:
        if 'root_dir' in locals() and root_dir.exists():
            shutil.rmtree(str(root_dir))
        raise RuntimeError(f"Failed to create environment: {e}") from e

async def cleanup_environment(env_id: str) -> None:
    """Clean up a runtime environment."""
    if env_id not in ENVIRONMENTS:
        return
        
    env = ENVIRONMENTS[env_id]
    try:
        if env.root_dir.exists():
            shutil.rmtree(str(env.root_dir))
    finally:
        del ENVIRONMENTS[env_id]