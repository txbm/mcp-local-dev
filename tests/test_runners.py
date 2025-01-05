import json
import pytest
import shutil
from pathlib import Path

from mcp_local_dev.test_runners.runners import detect_frameworks, run_framework_tests
from mcp_local_dev.test_runners.execution import auto_run_tests
from mcp_local_dev.types import Environment, RunConfig, TestRunnerType
from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command

@pytest.mark.asyncio
async def test_detect_frameworks(python_environment: Environment):
    """Test framework detection"""
    # First test with no frameworks
    frameworks = detect_frameworks(python_environment)
    assert len(frameworks) == 0
    
    # Install pytest
    await run_sandboxed_command(
        python_environment.sandbox,
        "python -m pip install pytest"
    )
    
    frameworks = detect_frameworks(python_environment)
    assert len(frameworks) == 1
    assert frameworks[0] == TestRunnerType.PYTEST

@pytest.mark.asyncio
async def test_run_framework_tests(python_environment: Environment):
    """Test running specific framework"""
    # Install pytest
    await run_sandboxed_command(
        python_environment.sandbox,
        "python -m pip install pytest"
    )
    
    # Setup test files
    fixtures_dir = Path(__file__).parent.parent / "fixtures_data" / "pytest"
    for src in fixtures_dir.glob("*.py"):
        shutil.copy(src, python_environment.sandbox.work_dir)
        
    config = RunConfig(
        framework=TestRunnerType.PYTEST,
        env=python_environment,
        test_dirs=[python_environment.sandbox.work_dir]
    )
    
    result = await run_framework_tests(config)
    assert result["success"] is True
    assert result["framework"] == "pytest"
    assert len(result["tests"]) > 0
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
    # Install pytest first
    await run_sandboxed_command(
        python_environment.sandbox,
        "python -m pip install pytest"
    )
    
    # Setup test files
    fixtures_dir = Path(__file__).parent.parent / "fixtures_data" / "pytest"
    for src in fixtures_dir.glob("*.py"):
        shutil.copy(src, python_environment.sandbox.work_dir)
        
    results = await auto_run_tests(python_environment)
    assert len(results) == 1
    assert results[0].type == "text"
    
    data = json.loads(results[0].text)
    
    assert data["success"] is True
    assert data["framework"] == "pytest"
    assert len(data["test_cases"]) > 0
    assert data["summary"]["passed"] > 0
