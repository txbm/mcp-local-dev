import pytest
from pathlib import Path

from mcp_runtime_server.testing.frameworks import detect_frameworks, run_framework_tests
from mcp_runtime_server.types import FrameworkType, RunConfig

@pytest.mark.asyncio
async def test_detect_and_run_pytest(python_environment):
    """Test framework detection and execution with real pytest project"""
    # Copy test project files to sandbox
    env = python_environment
    project_path = Path(__file__).parent
    # Copy sample test files to sandbox
    fixtures_dir = project_path / "fixtures"
    test_files = {
        "sample_test.py": "test_sample.py",
        "sample_conftest.py": "conftest.py"
    }
    for src_name, dst_name in test_files.items():
        src = fixtures_dir / src_name
        dst = env.sandbox.work_dir / dst_name
        dst.write_text(src.read_text())
    
    # Test framework detection
    frameworks = detect_frameworks(python_environment)
    assert frameworks == [FrameworkType.PYTEST]
    
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
