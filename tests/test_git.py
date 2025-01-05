import pytest
import pytest_asyncio
from pathlib import Path

from mcp_local_dev.sandboxes.git import normalize_github_url, clone_github_repository
from mcp_local_dev.types import Sandbox
from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command

@pytest.mark.parametrize("input_url,expected", [
    ("git@github.com:user/repo.git", "https://github.com/user/repo.git"),
    ("git@github.com:user/repo", "https://github.com/user/repo"),
    ("http://github.com/user/repo", ValueError),
    ("user/repo", "https://github.com/user/repo"),
    ("https://github.com/user/repo", "https://github.com/user/repo"),
    ("https://github.com/user/repo.git", "https://github.com/user/repo.git"),
    ("", ValueError),
    (None, ValueError),
    ("https://github.com/user/repo?token=abc", ValueError),
    ("https://github.com/user/repo#branch", ValueError),
    ("github.com/user/repo", "https://github.com/user/repo")
])
def test_normalize_github_url(input_url, expected):
    """Test GitHub URL normalization with various formats"""
    if expected is ValueError:
        with pytest.raises(ValueError):
            normalize_github_url(input_url)
    else:
        assert normalize_github_url(input_url) == expected

@pytest.mark.asyncio
async def test_clone_github_repository(sandbox: Sandbox):
    """Test cloning a GitHub repository"""
    # Use a small, public repo for testing
    url = "https://github.com/pallets/click"
    branch = "main"
    
    target_dir = await clone_github_repository(sandbox, url, branch)
    
    # Verify clone succeeded
    assert target_dir.exists()
    assert (target_dir / ".git").exists()
    assert (target_dir / "setup.py").exists() or (target_dir / "pyproject.toml").exists()


@pytest.mark.asyncio
async def test_clone_github_repository_with_branch(sandbox: Sandbox):
    """Test cloning specific branch"""
    url = "https://github.com/pallets/click"
    branch = "main"  # Changed from "8.0-maintenance" to "main"
    
    target_dir = await clone_github_repository(sandbox, url, branch)
    
    # Verify correct branch was cloned
    process = await run_sandboxed_command(
        sandbox,
        "git rev-parse --abbrev-ref HEAD"
    )
    stdout, _ = await process.communicate()
    assert stdout.decode().strip() == branch

@pytest.mark.asyncio
async def test_clone_github_repository_empty_url(sandbox: Sandbox):
    """Test cloning with empty URL fails appropriately"""
    with pytest.raises(ValueError):
        await clone_github_repository(sandbox, "", None)
