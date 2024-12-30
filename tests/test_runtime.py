"""Tests for runtime functionality."""
import pytest
import tempfile
from pathlib import Path

from mcp_runtime_server.types import RuntimeManager, RuntimeConfig
from mcp_runtime_server.environments import create_environment, cleanup_environment, ENVIRONMENTS


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.mark.asyncio
async def test_environment_cleanup(temp_dir):
    """Test environment cleanup."""
    config = RuntimeConfig(
        manager=RuntimeManager.UVX,
        github_url="https://github.com/test/repo"
    )
    
    env = await create_environment(config)
    assert env.id in ENVIRONMENTS
    
    await cleanup_environment(env.id)
    assert env.id not in ENVIRONMENTS


@pytest.mark.asyncio
async def test_environment_isolation(temp_dir):
    """Test that environments are properly isolated."""
    # Create two environments
    env1 = await create_environment(RuntimeConfig(
        manager=RuntimeManager.NPX,
        github_url="https://github.com/test/repo1"
    ))
    
    env2 = await create_environment(RuntimeConfig(
        manager=RuntimeManager.NPX,
        github_url="https://github.com/test/repo2"
    ))
    
    # Verify they have different working directories
    assert env1.root_dir != env2.root_dir
    assert env1.work_dir != env2.work_dir
    
    # Verify they have separate environment variables
    assert env1.env_vars != env2.env_vars
    
    # Clean up
    await cleanup_environment(env1.id)
    await cleanup_environment(env2.id)