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

@pytest.mark.asyncio
async def test_get_manager_binary(environment_per_manager):
    """Test manager binary resolution."""
    envs = await environment_per_manager
    
    # Test each manager binary
    for env in envs:
        binary = get_manager_binary(env.config.manager)
        assert binary.endswith(env.config.manager.value)
    
    # Invalid manager
    try:
        get_manager_binary(RuntimeManager("nonexistent"))
        pytest.fail("Expected RuntimeError")
    except RuntimeError as e:
        assert "Unsupported runtime manager" in str(e)

@pytest.mark.asyncio
async def test_build_install_command(environment_per_manager):
    """Test installation command building."""
    envs = await environment_per_manager
    npx_env = next(e for e in envs if e.config.manager == RuntimeManager.NPX)
    uvx_env = next(e for e in envs if e.config.manager == RuntimeManager.UVX) 
    pipx_env = next(e for e in envs if e.config.manager == RuntimeManager.PIPX)
    
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

@pytest.mark.asyncio
async def test_validate_package_name(environment_per_manager):
    """Test package name validation."""
    envs = await environment_per_manager
    
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

@pytest.mark.asyncio
async def test_prepare_env_vars(runtime_environment):
    """Test environment variable preparation."""
    env = await runtime_environment
    base_env = env.env_vars
    
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

@pytest.mark.asyncio
async def test_cleanup_manager_artifacts(environment_per_manager):
    """Test cleanup of manager artifacts."""
    envs = await environment_per_manager
    npx_env = next(e for e in envs if e.config.manager == RuntimeManager.NPX)
    uvx_env = next(e for e in envs if e.config.manager == RuntimeManager.UVX)
    
    # Create npm artifacts
    npm_artifacts = [
        npx_env.work_dir / "node_modules",
        npx_env.work_dir / "package.json",
        npx_env.work_dir / "package-lock.json"
    ]
    for artifact in npm_artifacts:
        if str(artifact).endswith("modules"):
            artifact.mkdir()
        else:
            artifact.touch()
    
    # Test NPX cleanup
    cleanup_manager_artifacts(RuntimeManager.NPX, str(npx_env.work_dir))
    for artifact in npm_artifacts:
        assert not artifact.exists()
    
    # Create Python artifacts
    python_artifacts = [
        uvx_env.work_dir / "__pycache__",
        uvx_env.work_dir / "test.pyc",
        uvx_env.work_dir / ".venv"
    ]
    for artifact in python_artifacts:
        if str(artifact).endswith(("__pycache__", ".venv")):
            artifact.mkdir()
        else:
            artifact.touch()
    
    # Test UVX cleanup
    cleanup_manager_artifacts(RuntimeManager.UVX, str(uvx_env.work_dir))
    for artifact in python_artifacts:
        assert not artifact.exists()

@pytest.mark.asyncio
async def test_prepare_env_vars_isolation(environment_per_manager):
    """Test that environment preparations are isolated."""
    envs = await environment_per_manager
    
    npx_env = next(e for e in envs if e.config.manager == RuntimeManager.NPX)
    uvx_env = next(e for e in envs if e.config.manager == RuntimeManager.UVX)
    
    base_env = npx_env.env_vars.copy()
    base_env["CUSTOM_VAR"] = "value"
    
    env1 = prepare_env_vars(RuntimeManager.NPX, base_env)
    env2 = prepare_env_vars(RuntimeManager.UVX, base_env)
    
    # Verify environments are different
    assert env1 != env2
    
    # Verify base environment wasn't modified
    assert "CUSTOM_VAR" in base_env
    assert base_env["CUSTOM_VAR"] == "value"
    
    # Verify each environment has its specific vars
    assert "NPX_NO_UPDATE_NOTIFIER" in env1
    assert "PIP_NO_CACHE_DIR" in env2

@pytest.mark.asyncio
async def test_multiple_version_formats(environment_per_manager):
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

@pytest.mark.asyncio
async def test_cleanup_nonexistent_path(environment_per_manager):
    """Test cleanup behavior with nonexistent paths."""
    envs = await environment_per_manager
    
    for env in envs:
        non_existent = env.work_dir / "nonexistent"
        cleanup_manager_artifacts(env.config.manager, str(non_existent))
        # Should not raise any errors