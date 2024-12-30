"""Test configuration and fixtures."""
import os
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from mcp_runtime_server.types import Environment, RuntimeConfig, RuntimeManager

def install_manager_binary(manager: RuntimeManager) -> Path:
    """Install runtime manager binary in temp environment."""
    install_scripts = {
        RuntimeManager.NPX: ["curl", "-L", "https://install-node.vercel.app"],
        RuntimeManager.BUN: ["curl", "-fsSL", "https://bun.sh/install"],
        RuntimeManager.UVX: ["pip", "install", "--user", "uv"],
        RuntimeManager.PIPX: ["pip", "install", "--user", "pipx"]
    }
    # TODO: Implement actual binary installation
    pass

@pytest.fixture
def runtime_environment():
    """Create test runtime environment with binaries."""
    with tempfile.TemporaryDirectory() as base_dir:
        # Create directory structure
        base_path = Path(base_dir)
        root_dir = base_path / "root"
        bin_dir = root_dir / "bin"
        work_dir = root_dir / "work"
        tmp_dir = root_dir / "tmp"
        
        for dir_path in [root_dir, bin_dir, work_dir, tmp_dir]:
            dir_path.mkdir(parents=True)
            
        # Create environment
        env = Environment(
            id="test-env",
            config=RuntimeConfig(
                github_url="https://github.com/test/repo",
                manager=RuntimeManager.NPX
            ),
            created_at=datetime.now(),
            root_dir=root_dir,
            bin_dir=bin_dir,
            work_dir=work_dir,
            tmp_dir=tmp_dir,
            env_vars={
                "PATH": str(bin_dir),
                "HOME": str(root_dir)
            }
        )
        
        # Install manager binaries
        install_manager_binary(env.config.manager)
        
        yield env

@pytest.fixture
def all_managers_environment():
    """Create environment with all runtime managers installed."""
    with tempfile.TemporaryDirectory() as base_dir:
        base_path = Path(base_dir)
        bin_dir = base_path / "bin"
        bin_dir.mkdir()
        
        # Install all managers
        for manager in RuntimeManager:
            install_manager_binary(manager)
            
        # Update PATH
        os.environ["PATH"] = f"{bin_dir}:{os.environ.get('PATH', '')}"
        
        yield bin_dir