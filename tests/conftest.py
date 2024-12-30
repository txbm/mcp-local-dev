"""Test configuration and fixtures."""
import pytest
import asyncio
from pathlib import Path

from mcp_runtime_server.types import RuntimeConfig, RuntimeManager
from mcp_runtime_server.environments import create_environment, cleanup_environment

@pytest.fixture(scope="function")
async def runtime_environment():
    """Create test runtime environment."""
    # Use a minimal test repo that exists
    config = RuntimeConfig(
        github_url="https://github.com/txbm/test-fixtures",
        manager=RuntimeManager.NPX
    )
    
    env = await create_environment(config)
    yield env
    await cleanup_environment(env.id)

@pytest.fixture(scope="function")
async def environment_per_manager():
    """Create environments for each runtime manager with manager binaries installed."""
    envs = []
    
    for manager in RuntimeManager:
        config = RuntimeConfig(
            github_url="https://github.com/txbm/test-fixtures",
            manager=manager
        )
        
        env = await create_environment(config)
        
        # Install manager binary in environment
        if manager == RuntimeManager.NPX:
            await _install_node_and_npm(env)
        elif manager == RuntimeManager.BUN:
            await _install_bun(env)
        elif manager == RuntimeManager.UVX:
            await _install_uv(env)
        elif manager == RuntimeManager.PIPX:
            await _install_pipx(env)
            
        envs.append(env)
    
    yield envs
    
    for env in envs:
        await cleanup_environment(env.id)

async def _install_node_and_npm(env):
    process = await asyncio.create_subprocess_shell(
        "curl -fsSL https://nodejs.org/dist/latest/node-v20.x.x.tar.gz | tar xz -C .",
        cwd=str(env.bin_dir),
        env=env.env_vars
    )
    await process.wait()

async def _install_bun(env):
    process = await asyncio.create_subprocess_shell(
        "curl -fsSL https://bun.sh/install | bash",
        cwd=str(env.bin_dir),
        env=env.env_vars
    )
    await process.wait()
    
async def _install_uv(env):
    process = await asyncio.create_subprocess_shell(
        "curl -LsSf https://astral.sh/uv/install.sh | sh",
        cwd=str(env.bin_dir),
        env=env.env_vars
    )
    await process.wait()

async def _install_pipx(env):
    process = await asyncio.create_subprocess_shell(
        "python -m pip install --user pipx",
        cwd=str(env.bin_dir),
        env=env.env_vars
    )
    await process.wait()