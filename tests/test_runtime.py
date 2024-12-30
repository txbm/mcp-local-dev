"""Tests for runtime management functionality."""
import os
import pytest
from datetime import datetime
import tempfile
from pathlib import Path

from mcp_runtime_server.types import RuntimeManager, RuntimeConfig, Environment
from mcp_runtime_server.runtime import (
    create_environment,
    cleanup_environment,
    ENVIRONMENTS
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
async def test_env(temp_dir):
    """Create a test environment."""
    config = RuntimeConfig(
        manager=RuntimeManager.UVX,
        github_url="https://github.com/test/repo"
    )
    env = await create_environment(config)
    yield env
    await cleanup_environment(env.id)


@pytest.mark.asyncio
async def test_create_environment(temp_dir):
    """Test environment creation."""
    config = RuntimeConfig(
        manager=RuntimeManager.NPX,
        github_url="https://github.com/test/repo"
    )
    
    env = await create_environment(config)
    
    assert env.id in ENVIRONMENTS
    assert env.config == config
    assert isinstance(env.created_at, datetime)
    assert isinstance(env.root_dir, Path)
    assert "HOME" in env.env_vars
    
    await cleanup_environment(env.id)


@pytest.mark.asyncio
async def test_cleanup_environment(temp_dir):
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