"""Tests for environment creation and lifecycle."""

import gc
import os
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
    assert env.runtime == Runtime.PYTHON

    # Check binary setup
    bin_name = "uv" if os.name != "nt" else "uv.exe"
    assert (env.sandbox.bin_dir / bin_name).exists()
    assert (env.sandbox.bin_dir / bin_name).stat().st_mode & 0o755 == 0o755

    # Verify environment variables
    assert str(env.sandbox.bin_dir) in env.env_vars["PATH"]
    assert env.env_vars["VIRTUAL_ENV"] == str(env.sandbox.work_dir / ".venv")

    cleanup_environment(env)
    assert not temp_root.exists()


@pytest.mark.asyncio
async def test_environment_implicit_cleanup():
    """Test environment cleanup when object is destroyed."""
    env = await create_environment("https://github.com/txbm/mcp-runtime-server.git")
    temp_root = Path(env.tempdir.name)
    assert temp_root.exists()

    temp_path = temp_root
    env = cast(Environment, None)
    gc.collect()

    assert not temp_path.exists()


@pytest.mark.asyncio
@pytest.mark.skip()
async def test_environment_cleanup_after_error():
    """Test environment cleanup after creation error."""
    with pytest.raises(RuntimeError):
        await create_environment("not-a-valid-url")

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
        assert env1.env_vars["VIRTUAL_ENV"] != env2.env_vars["VIRTUAL_ENV"]

        # Both should be Python with UV
        assert env1.runtime == Runtime.PYTHON
        assert env2.runtime == Runtime.PYTHON
        bin_name = "uv" if os.name != "nt" else "uv.exe"
        assert (env1.sandbox.bin_dir / bin_name).exists()
        assert (env2.sandbox.bin_dir / bin_name).exists()

    finally:
        cleanup_environment(env1)
        cleanup_environment(env2)

        assert not Path(env1.tempdir.name).exists()
        assert not Path(env2.tempdir.name).exists()


@pytest.mark.asyncio
async def test_environment_cleanup_twice():
    """Test that cleaning up an environment twice doesn't error."""
    env = await create_environment("https://github.com/txbm/mcp-runtime-server.git")
    temp_root = Path(env.tempdir.name)

    cleanup_environment(env)
    assert not temp_root.exists()

    cleanup_environment(env)  # Should not error