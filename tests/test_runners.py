import json
import pytest
import shutil
from pathlib import Path

from mcp_local_dev.test_runners.runners import detect_runners, run_tests
from mcp_local_dev.sandboxes.sandbox import create_sandbox
from mcp_local_dev.runtimes.runtime import detect_runtime
from mcp_local_dev.test_runners.execution import auto_run_tests
from mcp_local_dev.types import Environment, RunConfig, TestRunnerType
from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command

@pytest.mark.asyncio
async def test_detect_runners(python_environment: Environment):
    """Test runner detection"""
    # First test with no runners
    process = await run_sandboxed_command(
        python_environment.sandbox,
        "uv pip uninstall -y pytest"
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"Failed to uninstall pytest: {stderr.decode()}")

    # Verify no pytest
    runners = await detect_runners(python_environment)
    assert len(runners) == 0
    
    # Install pytest using UV
    process = await run_sandboxed_command(
        python_environment.sandbox,
        "uv pip install pytest"
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"Failed to install pytest: {stderr.decode()}")
    
    runners = await detect_runners(python_environment)
    assert len(runners) == 1
    assert runners[0] == TestRunnerType.PYTEST

@pytest.mark.asyncio
async def test_run_tests(python_environment: Environment):
    """Test running specific runner"""
    # Install pytest using UV
    process = await run_sandboxed_command(
        python_environment.sandbox,
        "uv pip install pytest"
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"Failed to install pytest: {stderr.decode()}")
    
    # Setup test files
    fixtures_dir = Path(__file__).parent.parent / "fixtures_data" / "pytest"
    for src in fixtures_dir.glob("*.py"):
        shutil.copy(src, python_environment.sandbox.work_dir)
        
    # Create __init__.py to make it a package
    (python_environment.sandbox.work_dir / "__init__.py").touch()
    
    config = RunConfig(
        runner=TestRunnerType.PYTEST,
        env=python_environment,
        test_dirs=[python_environment.sandbox.work_dir]
    )
    
    result = await run_tests(config)
    assert result["success"] is True
    assert result["summary"]["total"] > 0
    assert result["summary"]["passed"] > 0

@pytest.mark.asyncio
async def test_detect_runtime_invalid():
    """Test runtime detection with invalid project"""
    sandbox = await create_sandbox("test-")
    try:
        with pytest.raises(ValueError, match="No supported runtime detected"):
            detect_runtime(sandbox)
    finally:
        sandbox.temp_dir.cleanup()

@pytest.mark.asyncio
async def test_auto_run_tests(python_environment: Environment):
    """Test auto-detecting and running tests"""
    # Install pytest using UV
    process = await run_sandboxed_command(
        python_environment.sandbox,
        "uv pip install pytest"
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"Failed to install pytest: {stderr.decode()}")
    
    # Setup test files
    fixtures_dir = Path(__file__).parent.parent / "fixtures_data" / "pytest"
    for src in fixtures_dir.glob("*.py"):
        shutil.copy(src, python_environment.sandbox.work_dir)
        
    # Create __init__.py to make it a package
    (python_environment.sandbox.work_dir / "__init__.py").touch()
        
    results = await auto_run_tests(python_environment)
    assert len(results) == 1
    assert results[0].type == "text"
    
    data = json.loads(results[0].text)
    assert data["success"] is True
    assert data["summary"]["total"] > 0
    assert data["summary"]["passed"] > 0
