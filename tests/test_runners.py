import pytest
from pathlib import Path

from mcp_runtime_server.test_runners.execution import detect_test_runners, run_test_runner
from mcp_runtime_server.types import TestRunnerType, RunConfig

@pytest.mark.asyncio
async def test_detect_and_run_pytest(python_environment):
    """Test runner detection and execution with real pytest project"""
    # Copy test project files to sandbox
    env = python_environment
    project_path = Path(__file__).parent
    # Copy sample test files to sandbox
    fixtures_dir = project_path.parent / "fixtures_data" / "pytest"
    test_files = {
        "sample_test.py": "test_sample.py",
        "sample_conftest.py": "conftest.py"
    }
    for src_name, dst_name in test_files.items():
        src = fixtures_dir / src_name
        dst = env.sandbox.work_dir / dst_name
        dst.write_text(src.read_text())
    
    # Test runner detection
    runners = detect_test_runners(env)
    assert runners == [TestRunnerType.PYTEST]
    
    # Test running tests
    config = RunConfig(
        runner=TestRunnerType.PYTEST,
        env=env,
        test_dirs=[env.sandbox.work_dir]
    )
    results = await run_test_runner(config)
    
    assert results["success"] is True
    assert results["runner"] == "pytest"
    assert len(results["test_cases"]) > 0
    assert results["summary"]["passed"] > 0
