"""Tests for runtime functionality."""
import pytest
import tempfile
from pathlib import Path

from mcp_runtime_server.types import RuntimeManager, EnvironmentConfig
from mcp_runtime_server.environments import create_environment, cleanup_environment, ENVIRONMENTS


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
    assert env.manager == RuntimeManager.UVX  # Should detect Python project
    
    await cleanup_environment(env.id)
    assert env.id not in ENVIRONMENTS


@pytest.mark.asyncio
async def test_environment_isolation(temp_dir):
    """Test that environments are properly isolated."""
    # Create two environments cloning same Python repo
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
    assert env1.manager == RuntimeManager.UVX
    assert env2.manager == RuntimeManager.UVX
    
    # Clean up
    await cleanup_environment(env1.id)
    await cleanup_environment(env2.id)


@pytest.mark.asyncio
async def test_runtime_detection():
    """Test runtime detection for different project types."""
    node_config = EnvironmentConfig(
        github_url="https://github.com/vercel/next.js.git"
    )
    python_config = EnvironmentConfig(
        github_url="https://github.com/astral-sh/uv.git"
    )
    bun_config = EnvironmentConfig(
        github_url="https://github.com/oven-sh/bun.git"
    )
    
    node_env = await create_environment(node_config)
    assert node_env.manager == RuntimeManager.NPX
    
    python_env = await create_environment(python_config)
    assert python_env.manager == RuntimeManager.UVX
    
    bun_env = await create_environment(bun_config)
    assert bun_env.manager == RuntimeManager.BUN
    
    # Clean up
    await cleanup_environment(node_env.id)
    await cleanup_environment(python_env.id)
    await cleanup_environment(bun_env.id)