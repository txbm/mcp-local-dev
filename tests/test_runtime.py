"""Tests for runtime management functionality."""
import os
import pytest
from datetime import datetime
import tempfile
from pathlib import Path

from mcp_runtime_server.types import (
    RuntimeManager,
    RuntimeConfig,
    CaptureConfig,
    CaptureMode,
    ResourceLimits
)
from mcp_runtime_server.runtime import (
    create_environment,
    cleanup_environment,
    run_in_env,
    ACTIVE_ENVS
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
        package_name="cowsay",
        working_dir=temp_dir
    )
    env = await create_environment(config)
    yield env
    await cleanup_environment(env.id, force=True)


@pytest.mark.asyncio
async def test_create_environment(temp_dir):
    """Test environment creation."""
    config = RuntimeConfig(
        manager=RuntimeManager.NPX,
        package_name="chalk",
        working_dir=temp_dir,
        env={"TEST_VAR": "test_value"}
    )
    
    env = await create_environment(config)
    
    assert env.id in ACTIVE_ENVS
    assert env.config == config
    assert isinstance(env.created_at, datetime)
    assert env.working_dir == temp_dir
    assert env.env_vars.get("TEST_VAR") == "test_value"
    
    await cleanup_environment(env.id)


@pytest.mark.asyncio
async def test_run_command(test_env):
    """Test running a command in an environment."""
    result = await run_in_env(
        test_env.id,
        "python --version",
        CaptureConfig(mode=CaptureMode.BOTH)
    )
    
    assert result.exit_code == 0
    assert "Python" in result.stdout or "Python" in result.stderr
    assert isinstance(result.start_time, datetime)
    assert isinstance(result.end_time, datetime)


@pytest.mark.asyncio
async def test_resource_limits():
    """Test resource limits enforcement."""
    config = RuntimeConfig(
        manager=RuntimeManager.PIPX,
        package_name="memory-intensive-package",
        resource_limits=ResourceLimits(
            max_memory_mb=10,
            max_cpu_percent=50.0,
            timeout_seconds=1
        )
    )
    
    env = await create_environment(config)
    
    # Run a memory-intensive operation
    result = await run_in_env(
        env.id,
        'python -c "x = " + "a" * (1024 * 1024 * 20)"',  # Allocate 20MB
        CaptureConfig(mode=CaptureMode.BOTH, include_stats=True)
    )
    
    assert result.exit_code != 0  # Should be killed by resource limits
    if result.stats:
        assert result.stats.peak_memory_mb > 0
        assert result.stats.avg_cpu_percent >= 0
    
    await cleanup_environment(env.id)


@pytest.mark.asyncio
async def test_cleanup_environment(temp_dir):
    """Test environment cleanup."""
    config = RuntimeConfig(
        manager=RuntimeManager.UVX,
        package_name="requests",
        working_dir=temp_dir
    )
    
    env = await create_environment(config)
    assert env.id in ACTIVE_ENVS
    
    await cleanup_environment(env.id)
    assert env.id not in ACTIVE_ENVS


@pytest.mark.asyncio
async def test_parallel_commands(test_env):
    """Test running multiple commands in parallel."""
    import asyncio
    
    async def run_cmd(cmd: str) -> int:
        result = await run_in_env(
            test_env.id,
            cmd,
            CaptureConfig(mode=CaptureMode.BOTH)
        )
        return result.exit_code
    
    # Run multiple commands in parallel
    commands = [
        "python -c 'print(1)'",
        "python -c 'print(2)'",
        "python -c 'print(3)'"
    ]
    
    results = await asyncio.gather(*[
        run_cmd(cmd) for cmd in commands
    ])
    
    assert all(exit_code == 0 for exit_code in results)


@pytest.mark.asyncio
async def test_environment_isolation(temp_dir):
    """Test that environments are properly isolated."""
    # Create two environments
    env1 = await create_environment(RuntimeConfig(
        manager=RuntimeManager.NPX,
        package_name="chalk",
        working_dir=os.path.join(temp_dir, "env1")
    ))
    
    env2 = await create_environment(RuntimeConfig(
        manager=RuntimeManager.NPX,
        package_name="cowsay",
        working_dir=os.path.join(temp_dir, "env2")
    ))
    
    # Verify they have different working directories
    assert env1.working_dir != env2.working_dir
    
    # Verify they have separate environment variables
    assert env1.env_vars != env2.env_vars
    
    # Clean up
    await cleanup_environment(env1.id)
    await cleanup_environment(env2.id)