import pytest
import os
import shutil
from pathlib import Path
from mcp_local_dev.types import Sandbox, PackageManager
from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command, add_package_manager_bin_path

@pytest.mark.asyncio
async def test_sandbox_isolation(sandbox: Sandbox):
    """Test sandbox provides proper isolation"""
    # Test directory isolation
    sb = sandbox
    assert sb.work_dir.exists()
    assert sandbox.bin_dir.exists()
    assert sandbox.tmp_dir.exists()
    
    # Test environment isolation
    assert "TMPDIR" in sandbox.env_vars
    assert sandbox.env_vars["TMPDIR"] == str(sandbox.tmp_dir)
    assert "HOME" in sandbox.env_vars
    assert sandbox.env_vars["HOME"] == str(sandbox.work_dir)

@pytest.mark.asyncio
async def test_sandbox_command_execution(sandbox, fixture_path):
    """Test running commands in sandbox"""
    from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command
    
    # Copy test file from fixtures
    fixture_file = fixture_path / "test.txt"
    test_file = sandbox.work_dir / "test.txt"
    shutil.copy(fixture_file, test_file)
    
    # Run command in sandbox
    returncode, stdout, stderr = await run_sandboxed_command(sandbox, f"cat {test_file.name}")
    assert returncode == 0
    assert stdout.decode().strip() == "hello"

@pytest.mark.asyncio
async def test_add_package_manager_bin_path(sandbox: Sandbox):
    """Test package manager PATH updates"""
    original_path = sandbox.env_vars["PATH"]
    
    # Test UV
    add_package_manager_bin_path(sandbox, PackageManager.UV)
    assert str(sandbox.work_dir / ".venv" / "bin") in sandbox.env_vars["PATH"]
    
    # Test NPM
    add_package_manager_bin_path(sandbox, PackageManager.NPM)
    assert str(sandbox.work_dir / "node_modules" / ".bin") in sandbox.env_vars["PATH"]

@pytest.mark.asyncio
async def test_sandbox_environment_isolation(sandbox: Sandbox):
    """Test sandbox environment isolation"""
    returncode, stdout, _ = await run_sandboxed_command(
        sandbox,
        "env"
    )
    env_vars = dict(line.split("=", 1) for line in stdout.decode().splitlines() if "=" in line)
    
    assert env_vars["HOME"] == str(sandbox.work_dir)
    assert env_vars["TMPDIR"] == str(sandbox.tmp_dir)
    assert str(sandbox.bin_dir) in env_vars["PATH"]

def test_package_manager_path_order(sandbox: Sandbox):
    """Test package manager PATH is prepended correctly"""
    original_path = sandbox.env_vars["PATH"]
    add_package_manager_bin_path(sandbox, PackageManager.UV)
    new_path = sandbox.env_vars["PATH"]
    
    assert new_path.startswith(str(sandbox.work_dir / ".venv" / "bin"))
    assert original_path in new_path
