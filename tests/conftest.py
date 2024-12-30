"""Test configuration and fixtures."""
import pytest
import asyncio
from pathlib import Path

from mcp_runtime_server.types import RuntimeConfig, RuntimeManager
from mcp_runtime_server.environments import create_environment, cleanup_environment

@pytest.fixture(scope="function")
async def runtime_environment():
    """Create test runtime environment."""
    config = RuntimeConfig(
        github_url="https://github.com/txbm/mcp-runtime-server",
        manager=RuntimeManager.NPX
    )
    
    env = await create_environment(config)
    yield env
    await cleanup_environment(env.id)

@pytest.fixture(scope="function")
async def environment_per_manager():
    """Create environments for each runtime manager."""
    envs = []
    
    for manager in RuntimeManager:
        config = RuntimeConfig(
            github_url="https://github.com/txbm/mcp-runtime-server",
            manager=manager
        )
        env = await create_environment(config)
        envs.append(env)
    
    yield envs
    
    for env in envs:
        await cleanup_environment(env.id)