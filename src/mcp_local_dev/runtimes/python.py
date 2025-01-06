"""Python runtime implementation."""

import shutil
from pathlib import Path
from typing import List

from mcp_local_dev.types import Runtime, PackageManager, RuntimeConfig, Sandbox
from mcp_local_dev.sandboxes.commands import install_packages
from mcp_local_dev.sandboxes.sandbox import add_package_manager_bin_path

CONFIG = RuntimeConfig(
    name=Runtime.PYTHON,
    config_files=["pyproject.toml", "setup.py", "requirements.txt"],
    package_manager=PackageManager.UV,
    env_setup={
        "PYTHONUNBUFFERED": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    },
    binary_name="python",
    test_dependencies=[
        "pytest-cov>=4.1.0",
        "coverage>=7.4.0",  # For unittest coverage
    ],
)

async def setup_python(sandbox: Sandbox) -> None:
    """Set up Python runtime environment."""
    # Verify and symlink uv
    uv_path = shutil.which('uv')
    if not uv_path:
        raise RuntimeError("Required package manager not found: uv")

    target = sandbox.bin_dir / 'uv'
    if not target.exists():
        target.symlink_to(uv_path)

    # Set up environment variables
    for key, value in CONFIG.env_setup.items():
        sandbox.env_vars[key] = value

    # Add package manager bin paths before installing packages
    add_package_manager_bin_path(sandbox, CONFIG.package_manager)

    # Install project dependencies (uv sync will create venv automatically)
    await install_packages(sandbox, CONFIG.package_manager)
