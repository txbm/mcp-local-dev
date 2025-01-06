"""Node runtime implementation."""

import shutil
from pathlib import Path

from mcp_local_dev.types import Runtime, PackageManager, RuntimeConfig, Sandbox
from mcp_local_dev.sandboxes.commands import install_packages
from mcp_local_dev.sandboxes.sandbox import add_package_manager_bin_path

CONFIG = RuntimeConfig(
    name=Runtime.NODE,
    config_files=["package.json"],
    package_manager=PackageManager.NPM,
    env_setup={"NODE_NO_WARNINGS": "1"},
    binary_name="node",
)

async def setup_node(sandbox: Sandbox) -> None:
    """Set up Node runtime environment."""
    # Verify and symlink npm
    npm_path = shutil.which('npm')
    if not npm_path:
        raise RuntimeError("Required package manager not found: npm")

    target = sandbox.bin_dir / 'npm'
    if not target.exists():
        target.symlink_to(npm_path)

    # Set up environment variables
    for key, value in CONFIG.env_setup.items():
        sandbox.env_vars[key] = value

    # Add package manager bin paths before installing packages
    add_package_manager_bin_path(sandbox, CONFIG.package_manager)

    # Install project dependencies
    await install_packages(sandbox, CONFIG.package_manager)
