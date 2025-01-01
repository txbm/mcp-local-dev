"""Tests for runtime detection and management."""
import os
from pathlib import Path

import pytest
from mcp_runtime_server.types import Runtime, PackageManager
from mcp_runtime_server.environments.runtime import (
    detect_runtime, setup_runtime_env, get_package_manager_binary,
    get_runtime_bin_dir
)

def test_runtime_detection(tmp_path):
    """Test runtime detection from project files."""
    # Test Node.js
    pkg_json = tmp_path / "package.json"
    pkg_json.touch()
    assert detect_runtime(tmp_path) == Runtime.NODE

    # Test Bun
    bun_lock = tmp_path / "bun.lockb"
    bun_lock.touch()
    assert detect_runtime(tmp_path) == Runtime.BUN

    # Clean up for Python test
    pkg_json.unlink()
    bun_lock.unlink()

    # Test Python
    pyproject = tmp_path / "pyproject.toml"
    pyproject.touch()
    assert detect_runtime(tmp_path) == Runtime.PYTHON

    setup_py = tmp_path / "setup.py"
    setup_py.touch()
    assert detect_runtime(tmp_path) == Runtime.PYTHON

def test_runtime_detection_nested(tmp_path):
    """Test detection with nested config files."""
    nested = tmp_path / "src" / "project"
    nested.mkdir(parents=True)

    # Test Node detection
    pkg_json = nested / "package.json"
    pkg_json.touch()
    assert detect_runtime(tmp_path) == Runtime.NODE

    # Add bun.lockb, should switch to Bun
    bun_lock = nested / "bun.lockb"
    bun_lock.touch()
    assert detect_runtime(tmp_path) == Runtime.BUN

def test_runtime_detection_fails(tmp_path):
    """Test detection with no config files."""
    with pytest.raises(ValueError, match="No supported runtime detected"):
        detect_runtime(tmp_path)

def test_package_manager_mapping():
    """Test runtime to package manager mapping."""
    assert PackageManager.for_runtime(Runtime.PYTHON) == PackageManager.UV
    assert PackageManager.for_runtime(Runtime.NODE) == PackageManager.NPM
    assert PackageManager.for_runtime(Runtime.BUN) == PackageManager.BUN

def test_package_manager_binary():
    """Test package manager binary resolution."""
    binary = get_package_manager_binary(PackageManager.UV)
    assert binary.endswith(PackageManager.UV.value)

    with pytest.raises(RuntimeError):
        get_package_manager_binary("nonexistent")

def test_runtime_bin_dir(tmp_path):
    """Test runtime binary directory resolution."""
    # Test Python venv
    venv = tmp_path / ".venv"
    bin_dir = "Scripts" if os.name == "nt" else "bin"
    venv_bin = venv / bin_dir
    venv_bin.mkdir(parents=True)

    result = get_runtime_bin_dir(tmp_path, Runtime.PYTHON)
    assert result == venv_bin

    # Test Node modules
    node_bin = tmp_path / "node_modules" / ".bin"
    node_bin.mkdir(parents=True)

    result = get_runtime_bin_dir(tmp_path, Runtime.NODE)
    assert result == node_bin

def test_runtime_env_setup(tmp_path):
    """Test runtime environment variable setup."""
    base_env = {"PATH": "/usr/bin", "HOME": "/home/user"}

    # Test Python env
    venv = tmp_path / ".venv"
    bin_dir = venv / ("Scripts" if os.name == "nt" else "bin")
    bin_dir.mkdir(parents=True)

    env = setup_runtime_env(base_env, Runtime.PYTHON, tmp_path)
    assert str(bin_dir) in env["PATH"]
    assert env["VIRTUAL_ENV"] == str(venv)
    assert env["PYTHONPATH"] == str(tmp_path)

    # Test Node env
    node_bin = tmp_path / "node_modules" / ".bin"
    node_bin.mkdir(parents=True)

    env = setup_runtime_env(base_env, Runtime.NODE, tmp_path)
    assert str(node_bin) in env["PATH"]
    assert env["NODE_PATH"] == str(tmp_path / "node_modules")
    assert env["NODE_NO_WARNINGS"] == "1"