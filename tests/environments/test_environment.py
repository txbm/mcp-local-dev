"""Tests for environment creation and lifecycle."""

import gc
from pathlib import Path
from typing import cast

import pytest
from mcp_runtime_server.types import Runtime, Environment
from mcp_runtime_server.environments.environment import (
    create_environment,
    cleanup_environment,
)


@pytest.mark.asyncio
async def test_environment_creation():
    """Test environment creation with temp directory."""
    env = await create_environment("https://github.com/txbm/mcp-runtime-server.git")
    assert env.tempdir is not None

    temp_root = Path(env.tempdir.name)
    assert temp_root.exists()
    assert temp_root.name.startswith("mcp-")
    assert env.work_dir.exists()
    assert env.runtime == Runtime.PYTHON

    # Test explicit cleanup
    cleanup_environment(env)
    assert not temp_root.exists()


@pytest.mark.asyncio
async def test_environment_implicit_cleanup():
    """Test environment cleanup when object is destroyed."""
    env = await create_environment("https://github.com/txbm/mcp-runtime-server.git")
    temp_root = Path(env.tempdir.name)
    assert temp_root.exists()

    # Remove reference and force garbage collection
    temp_path = temp_root
    env = cast(Environment, None)
    gc.collect()

    # Directory should be cleaned up
    assert not temp_path.exists()


@pytest.mark.asyncio
@pytest.mark.skip()
async def test_environment_cleanup_after_error():
    """Test environment cleanup after creation error."""
    with pytest.raises(RuntimeError):
        # Invalid URL should cause failure
        await create_environment("not-a-valid-url")

    # Check for leftover directories
    assert not any(p for p in Path("/tmp").glob("mcp-*") if p.is_dir())


@pytest.mark.asyncio
async def test_environment_isolation():
    """Test environment isolation using temp directories."""
    env1 = await create_environment("https://github.com/txbm/mcp-runtime-server.git")
    env2 = await create_environment("https://github.com/txbm/mcp-runtime-server.git")

    try:
        # Check directories are isolated
        assert env1.tempdir.name != env2.tempdir.name
        assert env1.work_dir != env2.work_dir

        # Check env vars are isolated
        assert env1.env_vars["PATH"] != env2.env_vars["PATH"]

        # Both should be Python environments
        assert env1.runtime == Runtime.PYTHON
        assert env2.runtime == Runtime.PYTHON

        # Files should exist
        assert Path(env1.tempdir.name).exists()
        assert Path(env2.tempdir.name).exists()

    finally:
        cleanup_environment(env1)
        cleanup_environment(env2)

        # Verify cleanup
        assert not Path(env1.tempdir.name).exists()
        assert not Path(env2.tempdir.name).exists()


@pytest.mark.asyncio
async def test_environment_cleanup_twice():
    """Test that cleaning up an environment twice doesn't error."""
    env = await create_environment("https://github.com/txbm/mcp-runtime-server.git")
    temp_root = Path(env.tempdir.name)

    # First cleanup should work
    cleanup_environment(env)
    assert not temp_root.exists()

    # Second cleanup should not error
    cleanup_environment(env)
