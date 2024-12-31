"""Test framework utilities."""
import logging
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional
import re

from mcp_runtime_server.commands import run_command
from mcp_runtime_server.types import Environment

logger = logging.getLogger(__name__)

class TestFramework(str, Enum):
    PYTEST = "pytest"

def detect_frameworks(project_dir: str) -> List[TestFramework]:
    path = Path(project_dir)
    frameworks = set()
    
    tests_dir = path / 'tests'
    if tests_dir.exists():
        logger.debug(f"Found tests directory: {tests_dir}")
        conftest_path = tests_dir / 'conftest.py'
        if conftest_path.exists():
            frameworks.add(TestFramework.PYTEST)
            logger.debug(f"Found pytest config: {conftest_path}")

    logger.debug(f"Detected frameworks: {frameworks}")
    return list(frameworks)

def parse_pytest_output(output: str, errors: str) -> Dict[str, Any]:
    """Parse pytest output into structured results."""
    summary = {
        "passed": 0,
        "failed": 0,
        "total": 0,
        "failures": [],
        "errors": errors if errors else None
    }

    # Count test results
    for line in output.split('\n'):
        line = line.strip()
        if "PASSED" in line:
            summary["passed"] += 1
        elif "FAILED" in line:
            summary["failed"] += 1
            # Extract test name and failure message
            if "::" in line:
                test_info = line.split("[")[0].strip()
                summary["failures"].append({
                    "test": test_info,
                    "message": None  # Will be populated from error traces
                })
    
    # Extract detailed error messages
    error_details = []
    current_error = None
    for line in output.split('\n'):
        if line.startswith("tests/"):
            current_error = line
        elif current_error and line.strip().startswith("E "):
            error_details.append({
                "test": current_error,
                "message": line.strip()[2:]  # Remove "E " prefix
            })
            current_error = None

    summary["total"] = summary["passed"] + summary["failed"]
    if summary["failed"] > 0:
        summary["failures"] = error_details

    return summary

async def run_pytest(env: Environment) -> Dict[str, Any]:
    result = {
        "framework": TestFramework.PYTEST.value,
        "success": False
    }
    
    try:
        process = await run_command(
            "uv run python -m pytest -v tests/",
            str(env.work_dir),
            env.env_vars
        )
        stdout, stderr = await process.communicate()
        
        output = stdout.decode() if stdout else ""
        errors = stderr.decode() if stderr else ""
        
        # Parse test results
        summary = parse_pytest_output(output, errors)
        result.update(summary)
        result["success"] = summary["failed"] == 0
        
        logger.debug("Pytest execution completed", extra={
            "output": output,
            "errors": errors,
            "summary": summary
        })
        
    except Exception as e:
        result["error"] = str(e)
        logger.error("Pytest execution failed", extra={"error": str(e)})
        
    return result

async def run_framework_tests(framework: TestFramework, env: Environment) -> Dict[str, Any]:
    logger.debug(f"Running tests for framework: {framework}")
    if framework == TestFramework.PYTEST:
        return await run_pytest(env)
    else:
        raise ValueError(f"Unsupported framework: {framework}")
