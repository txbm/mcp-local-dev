"""Tests for environment creation and isolation."""
from pathlib import Path

from mcp_runtime_server.environments.environment import create_environment, cleanup_environment
from mcp_runtime_server.environments.runtime import Runtime

async def test_environment_creation(tmp_path):
    """Test basic environment creation."""
    env = await create_environment(
        tmp_path,
        "https://github.com/txbm/mcp-runtime-server.git"
    )
    try:
        # Check directory structure
        assert env.work_dir.exists()
        assert env.sandbox_root.exists()
        assert env.bin_dir.exists()
        
        # Check environment detection
        assert env.runtime == Runtime.PYTHON
        
        # Check environment variables
        assert "PATH" in env.env_vars
        assert str(env.bin_dir) in env.env_vars["PATH"]
        assert "VIRTUAL_ENV" in env.env_vars
        
    finally:
        cleanup_environment(env)

async def test_environment_isolation(tmp_path):
    """Test environment isolation."""
    env1 = await create_environment(
        tmp_path,
        "https://github.com/txbm/mcp-runtime-server.git"
    )
    env2 = await create_environment(
        tmp_path,
        "https://github.com/txbm/mcp-runtime-server.git"
    )
    
    try:
        # Check paths are isolated
        assert env1.sandbox_root != env2.sandbox_root
        assert env1.work_dir != env2.work_dir
        assert env1.bin_dir != env2.bin_dir
        
        # Check env vars are isolated
        assert env1.env_vars["PATH"] != env2.env_vars["PATH"]
        assert env1.env_vars["VIRTUAL_ENV"] != env2.env_vars["VIRTUAL_ENV"]
        
        # Both should be detected as Python projects
        assert env1.runtime == Runtime.PYTHON
        assert env2.runtime == Runtime.PYTHON
            
    finally:
        cleanup_environment(env1)
        cleanup_environment(env2)

async def test_environment_cleanup(tmp_path):
    """Test environment cleanup."""
    env = await create_environment(
        tmp_path,
        "https://github.com/txbm/mcp-runtime-server.git"
    )
    
    sandbox_root = env.sandbox_root
    work_dir = env.work_dir
    
    cleanup_environment(env)
    
    # Verify directories are gone
    assert not sandbox_root.exists()
    assert not work_dir.exists()

async def test_environment_creation_failure(tmp_path):
    """Test environment cleanup on creation failure."""
    with pytest.raises(RuntimeError):
        await create_environment(
            tmp_path,
            "https://nonexistent.invalid/repo.git"
        )
        
    # Verify no leftover directories
    assert not any(p for p in tmp_path.iterdir() if p.name.startswith("sandbox-"))