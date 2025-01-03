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


async def copy_binaries_to_dest(binaries: list[str], dest_dir: Path):
    for binary in binaries:
        if platform.system() == "Windows":
            which_cmd = ["where", binary]
        else:
            which_cmd = ["which", binary]

        returncode, stdout, stderr = await async_subprocess_run(*which_cmd)
        if returncode and returncode != 0:
            raise subprocess.CalledProcessError(returncode, which_cmd, stdout, stderr)

        binary_path = stdout.strip()
        destination_path = os.path.join(dest_dir, os.path.basename(binary_path))

        if platform.system() == "Darwin":
            cp_command = ["cp", "-p", "-X", binary_path, destination_path]
            returncode, _, _ = await async_subprocess_run(*cp_command)
            if returncode and returncode != 0:
                raise subprocess.CalledProcessError(returncode, cp_command)
        elif platform.system() == "Linux":
            cp_command = ["cp", "-p", "--preserve=all", binary_path, destination_path]
            returncode, _, _ = await async_subprocess_run(*cp_command)
            if returncode and returncode != 0:
                raise subprocess.CalledProcessError(returncode, cp_command)
        elif platform.system() == "Windows":
            shutil.copy(binary_path, destination_path)
        else:
            raise OSError("Unsupported operating system")

        logger.debug(
            {"event": "copy_sys_binary", "bin": binary, "dest": destination_path}
        )


def move_files(src: Path, dst: Path):

    for item in src.iterdir():
        if item.is_file():
            logger.debug({"event": "moving_file", "file": item, "dst": dst})
            shutil.move(str(item), str(dst))
