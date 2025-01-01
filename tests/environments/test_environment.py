"""Tests for environment creation and lifecycle."""
import os
from pathlib import Path

import pytest
from mcp_runtime_server.types import Runtime
from mcp_runtime_server.environments.environment import create_environment

@pytest.mark.asyncio
async def test_environment_creation():
    """Test environment creation with temp directory."""
    env = await create_environment("https://github.com/txbm/mcp-runtime-server.git")
    assert env._tempdir is not None
    
    temp_root = Path(env._tempdir.name)
    assert temp_root.exists()
    assert temp_root.name.startswith("mcp-")
    assert env.work_dir.exists()
    assert env.runtime == Runtime.PYTHON
    
    # Let Environment clean itself up
    env._tempdir.cleanup()
    assert not temp_root.exists()

@pytest.mark.asyncio
async def test_environment_isolation():
    """Test environment isolation using temp directories."""
    env1 = await create_environment("https://github.com/txbm/mcp-runtime-server.git")
    env2 = await create_environment("https://github.com/txbm/mcp-runtime-server.git")
    
    try:
        # Check directories are isolated
        assert env1._tempdir.name != env2._tempdir.name
        assert env1.work_dir != env2.work_dir
        
        # Check env vars are isolated
        assert env1.env_vars["PATH"] != env2.env_vars["PATH"]
        
        # Both should be Python environments
        assert env1.runtime == Runtime.PYTHON
        assert env2.runtime == Runtime.PYTHON
    
    finally:
        env1._tempdir.cleanup()
        env2._tempdir.cleanup()

@pytest.mark.asyncio
async def test_environment_cleanup():
    """Test environment cleanup with TemporaryDirectory."""
    env = await create_environment("https://github.com/txbm/mcp-runtime-server.git")
    temp_dir = Path(env._tempdir.name)
    work_dir = env.work_dir
    
    assert temp_dir.exists()
    assert work_dir.exists()
    
    env._tempdir.cleanup()
    assert not temp_dir.exists()
    assert not work_dir.exists()