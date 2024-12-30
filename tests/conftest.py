"""Test configuration and fixtures."""
import pytest
import asyncio
from datetime import datetime

from mcp_runtime_server.types import RuntimeConfig, RuntimeManager
from mcp_runtime_server.environments import create_environment, cleanup_environment

@pytest.fixture
async def runtime_environment():
    """Create test runtime environment."""
    config = RuntimeConfig(
        github_url="https://github.com/test/repo",
        manager=RuntimeManager.NPX
    )
    
    env = await create_environment(config)
    yield env
    await cleanup_environment(env.id)

@pytest.fixture
async def all_managers_environment():
    """Create environments for all runtime managers."""
    envs = []
    for manager in RuntimeManager:
        config = RuntimeConfig(
            github_url="https://github.com/test/repo",
            manager=manager
        )
        env = await create_environment(config)
        envs.append(env)
    
    yield envs
    
    for env in envs:
        await cleanup_environment(env.id)