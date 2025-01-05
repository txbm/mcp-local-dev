import pytest
import os
from pathlib import Path
from mcp_local_dev.types import Sandbox

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
async def test_sandbox_command_execution(sandbox):
    """Test running commands in sandbox"""
    from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command
    
    # Create test file
    sb = sandbox
    test_file = sb.work_dir / "test.txt"
    test_file.write_text("hello")
    
    # Run command in sandbox
    process = await run_sandboxed_command(sandbox, f"cat {test_file.name}")
    stdout, stderr = await process.communicate()
    
    assert process.returncode == 0
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
    process = await run_sandboxed_command(
        sandbox,
        "env"
    )
    stdout, _ = await process.communicate()
    env_vars = dict(line.split("=", 1) for line in stdout.decode().splitlines() if "=" in line)
    
    assert env_vars["HOME"] == str(sandbox.work_dir)
    assert env_vars["TMPDIR"] == str(sandbox.tmp_dir)
    assert str(sandbox.bin_dir) in env_vars["PATH"]
