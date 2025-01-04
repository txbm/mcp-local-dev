import asyncio
import os
import platform
import shutil
import subprocess
from pathlib import Path

from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


async def async_subprocess_run(*args):
    """
    Run a command asynchronously and return its exit code, stdout, and stderr.

    :param args: Command and arguments to run
    :return: Tuple of (returncode, stdout, stderr)
    """
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode(), stderr.decode()


async def copy_binary_to_dest(binary: str, dest_dir: Path) -> Path:
    """Copy a system binary to destination directory."""
    # Find binary path using appropriate command
    which_cmd = ["where", binary] if platform.system() == "Windows" else ["which", binary]
    
    returncode, stdout, stderr = await async_subprocess_run(*which_cmd)
    if returncode != 0:
        raise RuntimeError(f"Binary {binary} not found: {stderr}")
        
    binary_path = stdout.strip()
    dest_path = dest_dir / os.path.basename(binary_path)
    
    # Copy preserving permissions
    shutil.copy2(binary_path, dest_path)
    
    logger.debug({
        "event": "binary_copied",
        "source": binary_path,
        "destination": str(dest_path)
    })
    
    return dest_path


def move_files(src: Path, dst: Path):

    for item in src.iterdir():
        if item.is_file():
            logger.debug({"event": "moving_file", "file": item, "dst": dst})
            shutil.move(str(item), str(dst))
