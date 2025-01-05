"""Environment command execution."""

from mcp_local_dev.types import PackageManager, Sandbox
from mcp_local_dev.logging import get_logger
from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command

logger = get_logger(__name__)

async def install_packages(sandbox: Sandbox, pkg_manager: PackageManager) -> None:
    """Install project dependencies using the specified package manager."""
    if pkg_manager == PackageManager.UV:
        cmd = "uv sync --all-extras"
    elif pkg_manager == PackageManager.NPM:
        cmd = "npm install"
    elif pkg_manager == PackageManager.BUN:
        cmd = "bun install"
    else:
        raise RuntimeError(f"Unsupported package manager: {pkg_manager}")

    returncode, stdout, stderr = await run_sandboxed_command(sandbox, cmd)
    if returncode != 0:
        raise RuntimeError(
            f"Install failed with code {returncode}\n"
            f"stdout: {stdout.decode() if stdout else ''}\n"
            f"stderr: {stderr.decode() if stderr else ''}"
        )
