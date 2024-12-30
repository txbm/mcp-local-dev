"""Tests for runtime manager utilities."""
import os
import pytest
import tempfile
from pathlib import Path

from mcp_runtime_server.types import RuntimeManager
from mcp_runtime_server.managers import (
    get_manager_binary,
    build_install_command,
    validate_package_name,
    prepare_env_vars,
    cleanup_manager_artifacts
)


def test_get_manager_binary():
    """Test manager binary resolution."""
    # Test for non-existent binary
    with pytest.raises(RuntimeError):
        get_manager_binary(RuntimeManager("nonexistent"))


def test_build_install_command():
    """Test installation command building."""
    # NPX command
    cmd, args = build_install_command(
        RuntimeManager.NPX,
        "chalk",
        version="5.0.0",
        args=["--no-color"]
    )
    assert cmd.endswith("npx")
    assert "-y" in args
    assert "chalk@5.0.0" in args
    assert "--no-color" in args
    
    # UVX command
    cmd, args = build_install_command(
        RuntimeManager.UVX,
        "requests",
        version="2.31.0"
    )
    assert cmd.endswith("uvx")
    assert "--version" in args
    assert "2.31.0" in args
    assert "requests" in args
    
    # PIPX command without version
    cmd, args = build_install_command(
        RuntimeManager.PIPX,
        "black"
    )
    assert cmd.endswith("pipx")
    assert "run" in args
    assert "black" in args
    
    # Invalid manager
    with pytest.raises(RuntimeError):
        build_install_command(RuntimeManager("invalid"), "pkg")


def test_validate_package_name():
    """Test package name validation."""
    # NPM package names
    assert validate_package_name(RuntimeManager.NPX, "chalk")
    assert validate_package_name(RuntimeManager.NPX, "@types/node")
    assert validate_package_name(RuntimeManager.NPX, "@scope/package")
    assert not validate_package_name(RuntimeManager.NPX, "invalid$package")
    assert not validate_package_name(RuntimeManager.NPX, "")
    
    # Python package names
    assert validate_package_name(RuntimeManager.UVX, "requests")
    assert validate_package_name(RuntimeManager.UVX, "black-formatter")
    assert validate_package_name(RuntimeManager.UVX, "package.name")
    assert not validate_package_name(RuntimeManager.UVX, "invalid package")
    assert not validate_package_name(RuntimeManager.UVX, "")


def test_prepare_env_vars():
    """Test environment variable preparation."""
    base_env = {"PATH": "/usr/bin", "HOME": "/home/user"}
    
    # NPX environment
    npx_env = prepare_env_vars(RuntimeManager.NPX, base_env)
    assert npx_env["NPX_NO_UPDATE_NOTIFIER"] == "1"
    assert npx_env["PATH"] == base_env["PATH"]
    
    # UVX environment
    uvx_env = prepare_env_vars(RuntimeManager.UVX, base_env)
    assert "PIP_NO_CACHE_DIR" in uvx_env
    assert uvx_env["PATH"] == base_env["PATH"]
    
    # PIPX environment
    pipx_env = prepare_env_vars(RuntimeManager.PIPX, base_env)
    assert "PIPX_HOME" in pipx_env
    assert "PIPX_BIN_DIR" in pipx_env
    assert pipx_env["PATH"] == base_env["PATH"]


def test_cleanup_manager_artifacts():
    """Test cleanup of manager artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = Path(tmpdir)
        
        # Create some dummy artifacts
        npm_artifacts = [
            work_dir / "node_modules",
            work_dir / "package.json",
            work_dir / "package-lock.json"
        ]
        for artifact in npm_artifacts:
            if str(artifact).endswith("modules"):
                artifact.mkdir()
            else:
                artifact.touch()
        
        # Test NPX cleanup
        cleanup_manager_artifacts(RuntimeManager.NPX, str(work_dir))
        for artifact in npm_artifacts:
            assert not artifact.exists()
        
        # Create Python artifacts
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
        
        # Test UVX cleanup
        cleanup_manager_artifacts(RuntimeManager.UVX, str(work_dir))
        for artifact in python_artifacts:
            assert not artifact.exists()


def test_prepare_env_vars_isolation():
    """Test that environment preparations are isolated."""
    base_env = {"PATH": "/usr/bin", "CUSTOM_VAR": "value"}
    
    env1 = prepare_env_vars(RuntimeManager.NPX, base_env)
    env2 = prepare_env_vars(RuntimeManager.UVX, base_env)
    
    # Verify environments are different
    assert env1 != env2
    
    # Verify base environment wasn't modified
    assert len(base_env) == 2
    assert base_env["CUSTOM_VAR"] == "value"
    
    # Verify each environment has its specific vars
    assert "NPX_NO_UPDATE_NOTIFIER" in env1
    assert "PIP_NO_CACHE_DIR" in env2


def test_multiple_version_formats():
    """Test handling of different version formats."""
    # NPM style versions
    cmd, args = build_install_command(
        RuntimeManager.NPX,
        "package",
        version="^1.0.0"
    )
    assert "package@^1.0.0" in args
    
    # Python style versions
    cmd, args = build_install_command(
        RuntimeManager.PIPX,
        "package",
        version=">=2.0.0,<3.0.0"
    )
    assert "package==>=2.0.0,<3.0.0" in " ".join(args)


def test_cleanup_nonexistent_path():
    """Test cleanup behavior with nonexistent paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        non_existent = os.path.join(tmpdir, "nonexistent")
        
        # Should not raise any errors
        cleanup_manager_artifacts(RuntimeManager.NPX, non_existent)
        cleanup_manager_artifacts(RuntimeManager.UVX, non_existent)