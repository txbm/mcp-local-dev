"""Tests for runtime manager utilities."""
import os
import pytest
from pathlib import Path

from mcp_runtime_server.types import RuntimeManager
from mcp_runtime_server.managers import (
    get_manager_binary,
    build_install_command,
    prepare_env_vars,
    cleanup_manager_artifacts
)

def test_get_manager_binary(mocker):
    """Test manager binary resolution."""
    # Mock shutil.which to return predictable paths
    mocker.patch('shutil.which', side_effect=lambda x: f"/usr/bin/{x}")
    
    # Test each manager binary
    for manager in RuntimeManager:
        binary = get_manager_binary(manager)
        assert binary == f"/usr/bin/{manager.value}"
    
    # Test nonexistent binary
    mocker.patch('shutil.which', return_value=None)
    with pytest.raises(RuntimeError, match="Runtime nonexistent not found"):
        get_manager_binary("nonexistent")

def test_build_install_command():
    """Test installation command building."""
    # Node
    cmd, args = build_install_command(RuntimeManager.NODE)
    assert cmd.endswith("npm")
    assert args == ["install"]
    
    cmd, args = build_install_command(RuntimeManager.NODE, args=["--production"])
    assert args == ["install", "--production"]
    
    # Bun
    cmd, args = build_install_command(RuntimeManager.BUN)
    assert cmd.endswith("bun")
    assert args == ["install"]
    
    cmd, args = build_install_command(RuntimeManager.BUN, args=["--production"])
    assert args == ["install", "--production"]
    
    # UV
    cmd, args = build_install_command(RuntimeManager.UV)
    assert cmd.endswith("uv")
    assert args == ["sync"]
    
    cmd, args = build_install_command(RuntimeManager.UV, args=["--system"])
    assert args == ["sync", "--system"]

def test_prepare_env_vars():
    """Test environment variable preparation."""
    base_env = {
        "PATH": "/usr/bin",
        "HOME": "/home/user"
    }
    
    # Node environment
    node_env = prepare_env_vars(RuntimeManager.NODE, base_env)
    assert node_env["NODE_NO_WARNINGS"] == "1"
    assert node_env["NPM_CONFIG_UPDATE_NOTIFIER"] == "false"
    assert node_env["PATH"] == base_env["PATH"]
    
    # Bun environment
    bun_env = prepare_env_vars(RuntimeManager.BUN, base_env)
    assert bun_env["NO_INSTALL_HINTS"] == "1"
    assert bun_env["PATH"] == base_env["PATH"]
    
    # UV environment
    uv_env = prepare_env_vars(RuntimeManager.UV, base_env)
    assert uv_env["PIP_NO_CACHE_DIR"] == "1"
    assert uv_env["PATH"] == base_env["PATH"]

def test_cleanup_manager_artifacts(tmp_path):
    """Test cleanup of manager artifacts."""
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    
    # Test Node/Bun cleanup
    node_artifacts = [
        work_dir / "node_modules",
        work_dir / ".npm"
    ]
    for artifact in node_artifacts:
        if str(artifact).endswith(("modules", ".npm")):
            artifact.mkdir()
    
    cleanup_manager_artifacts(RuntimeManager.NODE, str(work_dir))
    for artifact in node_artifacts:
        assert not artifact.exists()
    
    # Test Bun-specific cleanup
    bun_artifacts = [
        work_dir / "node_modules",
        work_dir / "bun.lockb",
        work_dir / ".bun"
    ]
    for artifact in bun_artifacts:
        if str(artifact).endswith(("modules", ".bun")):
            artifact.mkdir()
        else:
            artifact.touch()
    
    cleanup_manager_artifacts(RuntimeManager.BUN, str(work_dir))
    for artifact in bun_artifacts:
        assert not artifact.exists()
    
    # Test UV cleanup
    python_artifacts = [
        work_dir / "__pycache__",
        work_dir / "test.pyc",
        work_dir / ".venv"
    ]
    for artifact in python_artifacts:
        if str(artifact).endswith(("__pycache__", ".venv")):
            artifact.mkdir()
        else:
            artifact.touch()
    
    cleanup_manager_artifacts(RuntimeManager.UV, str(work_dir))
    for artifact in python_artifacts:
        assert not artifact.exists()

def test_prepare_env_vars_isolation():
    """Test that environment preparations are isolated."""
    base_env = {
        "PATH": "/usr/bin",
        "HOME": "/home/user",
        "CUSTOM_VAR": "value"
    }
    
    env1 = prepare_env_vars(RuntimeManager.NODE, base_env)
    env2 = prepare_env_vars(RuntimeManager.UV, base_env)
    
    # Verify environments are different
    assert env1 != env2
    
    # Verify base environment wasn't modified
    assert base_env["CUSTOM_VAR"] == "value"
    
    # Verify each environment has its specific vars
    assert "NODE_NO_WARNINGS" in env1
    assert "PIP_NO_CACHE_DIR" in env2

def test_cleanup_nonexistent_path(tmp_path):
    """Test cleanup behavior with nonexistent paths."""
    non_existent = tmp_path / "nonexistent"
    for manager in RuntimeManager:
        cleanup_manager_artifacts(manager, str(non_existent))
        # Should not raise any errors