import json
import pytest
import shutil
from pathlib import Path

from mcp_local_dev.test_runners.execution import auto_run_tests
from mcp_local_dev.types import Environment
from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command

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
    
    assert results["success"] is True
    assert results["runner"] == "pytest"
    assert len(results["test_cases"]) > 0
    assert results["summary"]["passed"] > 0
