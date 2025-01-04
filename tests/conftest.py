import pytest
import pytest_asyncio
import asyncio
from pathlib import Path
from datetime import datetime, timezone

from mcp_local_dev.types import Environment, RuntimeConfig, Sandbox, Runtime, PackageManager
from mcp_local_dev.sandboxes.sandbox import create_sandbox

@pytest_asyncio.fixture
async def sandbox():
    """Create a real temporary sandbox for testing"""
    sandbox = await create_sandbox("test-")
    try:
        yield sandbox
    finally:
        sandbox.temp_dir.cleanup()

@pytest_asyncio.fixture
async def python_runtime_config():
    """Standard Python runtime config"""
    return RuntimeConfig(
        name=Runtime.PYTHON,
        config_files=["pyproject.toml", "setup.py", "requirements.txt"],
        package_manager=PackageManager.UV,
        env_setup={
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        binary_name="python"
    )

@pytest_asyncio.fixture
async def python_environment(sandbox, python_runtime_config):
    """Create a real Python environment with sandbox"""
    env = Environment(
        id="test-env-1",
        runtime_config=python_runtime_config,
        created_at=datetime.now(timezone.utc),
        sandbox=sandbox
    )
    yield env
