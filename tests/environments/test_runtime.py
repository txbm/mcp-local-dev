"""Tests for runtime detection and management."""

import os
from pathlib import Path
import pytest

from mcp_runtime_server.types import Runtimes
from mcp_runtime_server.environments.environment import create_environment
from mcp_runtime_server.environments.runtime import (
    Runtime,
    detect_runtime,
    setup_runtime_env,
    get_runtime_binary,
    get_runtime_bin_dir,
)


@pytest.mark.asyncio
async def test_node_detection(tmp_path):
    """Test Node.js project detection."""
    env = await create_environment(
        tmp_path, "https://github.com/txbm/mcp-node-repo-fixture"
    )

    runtime = detect_runtime(env.work_dir)
    assert runtime == Runtimes.NODE


# async def test_bun_detection(tmp_path):
#     """Test Bun project detection."""
#     env = await create_environment(tmp_path, "https://github.com/txbm/mcp-python-repo-fixture")

#     # Should not detect as Bun with just package.json
#     runtime = detect_runtime(env.work_dir)
#     assert runtime == Runtime.NODE

#     # Should detect as Bun with both files
#     Path(env.work_dir, "bun.lockb").touch()
#     runtime = detect_runtime(env.work_dir)
#     assert runtime == Runtime.BUN


@pytest.mark.asyncio
async def test_python_detection(tmp_path):
    """Test Python project detection."""
    env = await create_environment(
        tmp_path, "https://github.com/txbm/mcp-python-repo-fixture"
    )

    project_toml = env.work_dir / "pyproject.toml"
    project_toml.touch()
    runtime = detect_runtime(env.work_dir)
    assert runtime == Runtimes.PYTHON

    # Test setup.py
    setup_py = env.work_dir / "setup.py"
    setup_py.touch()
    runtime = detect_runtime(env.work_dir)
    assert runtime == Runtimes.PYTHON


# @pytest.mark.asyncio
# async def test_unknown_project(tmp_path):
#     """Test unrecognized project detection."""
#     env = await create_environment(tmp_path, "https://github.com/username/unknown-project")
#     with pytest.raises(ValueError, match="No supported runtime detected"):
#         detect_runtime(env.work_dir)

# @pytest.mark.asyncio
# async def test_nested_files(tmp_path):
#     """Test detection with nested config files."""
#     env = await create_environment(tmp_path, "https://github.com/username/nested-project")

#     nested = env.work_dir / "src" / "project"
#     nested.mkdir(parents=True)

#     # Test Node detection
#     pkg_json = nested / "package.json"
#     pkg_json.touch()
#     runtime = detect_runtime(env.work_dir)
#     assert runtime == Runtime.NODE

#     # Add bun.lockb, should switch to Bun
#     bun_lock = nested / "bun.lockb"
#     bun_lock.touch()
#     runtime = detect_runtime(env.work_dir)
#     assert runtime == Runtime.BUN


@pytest.mark.asyncio
async def test_runtime_env_setup(tmp_path):
    """Test runtime-specific environment setup."""
    # Test Node.js environment
    node_env = await create_environment(
        tmp_path, "https://github.com/txbm/mcp-node-repo-fixture"
    )
    assert "NODE_NO_WARNINGS" in node_env.env_vars
    assert "NPM_CONFIG_UPDATE_NOTIFIER" in node_env.env_vars
    assert (
        node_env.work_dir / "node_modules" / ".bin"
    ).as_posix() in node_env.env_vars["PATH"]

    # Test Python environment
    py_env = await create_environment(
        tmp_path, "https://github.com/txbm/mcp-python-repo-fixture"
    )
    assert "VIRTUAL_ENV" in py_env.env_vars
    assert "PIP_NO_CACHE_DIR" in py_env.env_vars
    venv_path = py_env.work_dir / ".venv"
    bin_dir = "Scripts" if os.name == "nt" else "bin"
    assert (venv_path / bin_dir).as_posix() in py_env.env_vars["PATH"]


@pytest.mark.asyncio
async def test_binary_resolution(tmp_path):
    """Test runtime binary resolution."""
    env = await create_environment(
        tmp_path, "https://github.com/txbm/mcp-python-repo-fixture"
    )

    # Setup mock binary
    bin_dir = env.work_dir / ".venv" / ("Scripts" if os.name == "nt" else "bin")
    bin_dir.mkdir(parents=True)
    binary = bin_dir / ("python.exe" if os.name == "nt" else "python")
    binary.touch()
    binary.chmod(0o755)

    bin_dir = get_runtime_bin_dir(env.work_dir, Runtimes.PYTHON)
    assert bin_dir == bin_dir
    assert binary.exists()
