"""Tests for runtime functionality."""

import pytest
import tempfile
from pathlib import Path

from mcp_runtime_server.types import RuntimeManager, EnvironmentConfig
from mcp_runtime_server.environments import (
    create_environment,
    cleanup_environment,
    ENVIRONMENTS,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.mark.asyncio
async def test_environment_cleanup(temp_dir):
    """Test environment cleanup."""
    config = EnvironmentConfig(
        github_url="https://github.com/txbm/mcp-runtime-server.git"
    )

    env = await create_environment(config)
    assert env.id in ENVIRONMENTS
    assert env.manager == RuntimeManager.UV  # Should detect Python project
    assert env._temp_dir is not None  # Verify temp dir is managed

    cleanup_environment(env.id)
    assert env.id not in ENVIRONMENTS


@pytest.mark.asyncio
async def test_environment_isolation(temp_dir):
    """Test that environments are properly isolated."""
    config = EnvironmentConfig(
        github_url="https://github.com/txbm/mcp-runtime-server.git"
    )

    env1 = await create_environment(config)
    env2 = await create_environment(config)

    # Verify they have different working directories
    assert env1.root_dir != env2.root_dir
    assert env1.work_dir != env2.work_dir

    # Verify they have separate environment variables
    assert env1.env_vars != env2.env_vars

    # Both should detect as Python/UV projects
    assert env1.manager == RuntimeManager.UV
    assert env2.manager == RuntimeManager.UV

    # Verify temp dirs are managed
    assert env1._temp_dir is not None
    assert env2._temp_dir is not None

    # Clean up
    cleanup_environment(env1.id)
    cleanup_environment(env2.id)


@pytest.mark.asyncio
async def test_environment_error_cleanup(temp_dir):
    """Test environment cleanup on creation error."""
    config = EnvironmentConfig(
        github_url="https://nonexistent.invalid/repo.git"
    )

    with pytest.raises(RuntimeError):
        await create_environment(config)