"""Environment command execution."""


from mcp_local_dev.types import PackageManager, Environment
from mcp_local_dev.logging import get_logger
from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command

logger = get_logger(__name__)


async def run_install(env: Environment) -> None:
    """Run install command for environment runtime."""
    pkg_manager = env.runtime_config.package_manager
    pkg_bin = env.sandbox.bin_dir / pkg_manager.value.lower()
    
    if not pkg_bin.exists():
        raise RuntimeError(f"Package manager binary not found: {pkg_bin}")

    # Get the appropriate install command for package manager
    if pkg_manager == PackageManager.UV:
        cmd = "uv sync --all-extras"
    elif pkg_manager == PackageManager.NPM:
        cmd = "npm install"
    elif pkg_manager == PackageManager.BUN:
        cmd = "bun install"
    else:
        raise RuntimeError(f"Unsupported package manager: {pkg_manager}")

    process = await run_sandboxed_command(env.sandbox, cmd)
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(
            f"Install failed with code {process.returncode}\n"
            f"stdout: {stdout.decode()}\n"
            f"stderr: {stderr.decode()}"
        )
