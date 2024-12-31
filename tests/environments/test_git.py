"""Tests for Git operations."""
import os
from pathlib import Path

from mcp_runtime_server.environments.environment import create_environment
from mcp_runtime_server.git import clone_repository

async def test_github_clone(tmp_path):
    """Test GitHub repository cloning during environment creation."""
    env = await create_environment(
        tmp_path,
        "https://github.com/txbm/mcp-runtime-server"
    )
    
    # Verify clone success
    assert (env.work_dir / ".git").exists()
    assert (env.work_dir / "pyproject.toml").exists()

async def test_invalid_url(tmp_path):
    """Test environment creation with invalid Git URL."""
    with pytest.raises(RuntimeError):
        await create_environment(
            tmp_path,
            "not-a-url"
        )
