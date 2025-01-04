import pytest
from pathlib import Path

from mcp_runtime_server.testing.frameworks import detect_frameworks, run_framework_tests
from mcp_runtime_server.types import TestFramework, RunConfig

@pytest.mark.asyncio
async def test_detect_and_run_pytest(python_environment):
    """Test framework detection and execution with real pytest project"""
    # Copy test project files to sandbox
    project_path = Path(__file__).parent
    test_files = [
        "test_sample.py",
        "conftest.py"
    ]
    for file in test_files:
        src = project_path / file
        dst = python_environment.sandbox.work_dir / file
        dst.write_text(src.read_text())
    
    # Test framework detection
    frameworks = detect_frameworks(python_environment)
    assert frameworks == [TestFramework.PYTEST]
    
    # Test running tests
    config = RunConfig(
        framework=TestFramework.PYTEST,
        env=python_environment,
        test_dirs=[python_environment.sandbox.work_dir]
    )
    results = await run_framework_tests(config)
    
    assert results["success"] is True
    assert results["framework"] == "pytest"
    assert results["total"] > 0
    assert results["passed"] > 0
