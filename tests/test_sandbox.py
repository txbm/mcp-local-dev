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
