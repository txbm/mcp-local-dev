"""Tests for Git operations."""
import os
import pytest
import tempfile
from pathlib import Path

from mcp_runtime_server.git import clone_repository


@pytest.mark.asyncio
async def test_github_clone():
    """Test GitHub repository cloning."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "repo"
        env_vars = {"HOME": str(tmpdir), "PATH": os.environ["PATH"]}
        
        await clone_repository(
            "github.com/txbm/mcp-runtime-server",
            str(target),
            env_vars
        )
        
        # Verify clone success
        assert target.exists()
        assert (target / ".git").exists()
        assert (target / "pyproject.toml").exists()


@pytest.mark.asyncio
async def test_invalid_repo():
    """Test cloning invalid repository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "repo"
        env_vars = {"HOME": str(tmpdir), "PATH": os.environ["PATH"]}
        
        with pytest.raises(RuntimeError) as exc:
            await clone_repository(
                "github.com/txbm/nonexistent-repo",
                str(target),
                env_vars
            )
        assert "Clone failed" in str(exc.value)
        assert not target.exists()


@pytest.mark.asyncio
async def test_invalid_url():
    """Test cloning with invalid URL format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "repo"
        env_vars = {"HOME": str(tmpdir), "PATH": os.environ["PATH"]}
        
        with pytest.raises(RuntimeError):
            await clone_repository(
                "not-a-url",
                str(target), 
                env_vars
            )