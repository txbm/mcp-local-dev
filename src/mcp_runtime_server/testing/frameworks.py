"""Test framework utilities."""

import logging
import os
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any

from mcp_runtime_server.commands import run_command
from mcp_runtime_server.types import Environment

logger = logging.getLogger(__name__)

class TestFramework(str, Enum):
    """Test framework types."""
    UNITTEST = "unittest"
    PYTEST = "pytest"

def detect_frameworks(project_dir: str) -> List[TestFramework]:
    """Detect test frameworks used in project."""
    path = Path(project_dir)
    frameworks = []
    
    # Look for unit test files
    if any(str(f).endswith('_test.py') or str(f).startswith('test_') for f in path.rglob('*.py')):
        frameworks.append(TestFramework.UNITTEST)
    
    # Look for pytest files and configuration
    if any(str(f).endswith('_test.py') or str(f).startswith('test_') for f in path.rglob('*.py')):
        if any(str(f).endswith(('pytest.ini', 'conftest.py', 'tox.ini')) for f in path.rglob('*')):
            frameworks.append(TestFramework.PYTEST)
    
    return frameworks

async def run_unittest(env: Environment) -> Dict[str, Any]:
    """Run Python unittest tests."""
    result = {
        "framework": TestFramework.UNITTEST.value,
        "success": False
    }
    
    try:
        process = await run_command(
            "python -m unittest discover -v",
            str(env.work_dir),
            env.env_vars
        )
        stdout, stderr = await process.communicate()
        
        result["output"] = stdout.decode() if stdout else ""
        result["errors"] = stderr.decode() if stderr else ""
        result["success"] = process.returncode == 0
        
    except Exception as e:
        result["errors"] = str(e)
        
    return result

async def run_pytest(env: Environment) -> Dict[str, Any]:
    """Run pytest tests."""
    result = {
        "framework": TestFramework.PYTEST.value,
        "passed": 0,
        "failed": 0,
        "total": 0,
        "failures": [],
        "coverage": None
    }
    
    try:
        process = await run_command(
            "python -m pytest -v",
            str(env.work_dir),
            env.env_vars
        )
        stdout, stderr = await process.communicate()
        
        output = stdout.decode() if stdout else ""
        errors = stderr.decode() if stderr else ""
        
        # Parse test results
        result["success"] = process.returncode == 0
        
        # Basic result parsing (could be enhanced)
        for line in output.split('\n'):
            if 'passed' in line.lower():
                result["passed"] += 1
            elif 'failed' in line.lower():
                result["failed"] += 1
                result["failures"].append(line)
        
        result["total"] = result["passed"] + result["failed"]
        
    except Exception as e:
        result["errors"] = str(e)
        result["success"] = False
        
    return result

async def run_framework_tests(framework: TestFramework, env: Environment) -> Dict[str, Any]:
    """Run tests for a specific framework."""
    if framework == TestFramework.UNITTEST:
        return await run_unittest(env)
    elif framework == TestFramework.PYTEST:
        return await run_pytest(env)
    else:
        raise ValueError(f"Unsupported framework: {framework}")
