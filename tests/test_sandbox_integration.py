"""Integration tests for sandbox functionality."""
import pytest
import tempfile
from pathlib import Path

from mcp_runtime_server.types import Environment, RuntimeManager, EnvironmentConfig
from mcp_runtime_server.environments import create_environment, cleanup_environment


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
async def test_env(temp_dir):
    """Create a test environment."""
    config = EnvironmentConfig(
        github_url="https://github.com/txbm/mcp-runtime-server.git"
    )
    env = await create_environment(config)
    yield env
    await cleanup_environment(env.id)


@pytest.mark.asyncio
async def test_environment_isolation(temp_dir):
    """Test environment isolation."""
    config = EnvironmentConfig(
        github_url="https://github.com/txbm/mcp-runtime-server.git"
    )
    
    env1 = await create_environment(config)
    env2 = await create_environment(config)
    
    try:
        # Check paths are isolated
        assert env1.root_dir != env2.root_dir
        assert env1.bin_dir != env2.bin_dir
        assert env1.tmp_dir != env2.tmp_dir
        
        # Check env vars are isolated  
        for key in ["HOME", "TMPDIR", "PATH"]:
            assert env1.env_vars[key] != env2.env_vars[key]
            
        # Both should detect as Python projects
        assert env1.manager == RuntimeManager.UVX
        assert env2.manager == RuntimeManager.UVX
            
    finally:
        await cleanup_environment(env1.id)
        await cleanup_environment(env2.id)