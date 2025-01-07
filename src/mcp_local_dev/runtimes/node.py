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
    # Verify and symlink node and npm
    node_path = shutil.which('node')
    if not node_path:
        raise RuntimeError("Required runtime not found: node")

    npm_path = shutil.which('npm')
    if not npm_path:
        raise RuntimeError("Required package manager not found: npm")

    # Symlink node
    node_target = sandbox.bin_dir / 'node'
    if not node_target.exists():
        node_target.symlink_to(node_path)

    # Symlink npm and npx
    npm_target = sandbox.bin_dir / 'npm'
    if not npm_target.exists():
        npm_target.symlink_to(npm_path)

    npx_path = shutil.which('npx')
    if not npx_path:
        raise RuntimeError("Required package manager not found: npx")

    npx_target = sandbox.bin_dir / 'npx'
    if not npx_target.exists():
        npx_target.symlink_to(npx_path)

    # Set up environment variables
    for key, value in CONFIG.env_setup.items():
        sandbox.env_vars[key] = value

    # Add package manager bin paths before installing packages
    add_package_manager_bin_path(sandbox, CONFIG.package_manager)

    # Install project dependencies
    await install_packages(sandbox, CONFIG.package_manager)
