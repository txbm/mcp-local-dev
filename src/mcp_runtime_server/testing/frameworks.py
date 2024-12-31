"""Test framework utilities."""
import logging
import re
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional

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
    result = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "total": 0,
        "failures": [],
        "stdout": output,
        "stderr": errors,
        "warnings": [],
        "test_cases": []
    }

    current_test = None

    for line in output.split('\n'):
        line = line.strip()
        
        if "collected" in line and "item" in line:
            match = re.search(r"collected\s+(\d+)\s+item", line)
            if match:
                result["total"] = int(match.group(1))
                
        elif "::" in line and any(status in line for status in ["PASSED", "FAILED", "SKIPPED"]):
            test_name = line.split("[")[0].strip()
            status = "passed" if "PASSED" in line else "failed" if "FAILED" in line else "skipped"
            current_test = {
                "name": test_name,
                "status": status,
                "output": [],
                "failureMessage": None if status != "failed" else ""
            }
            result["test_cases"].append(current_test)
            
            if status == "passed":
                result["passed"] += 1
            elif status == "failed":
                result["failed"] += 1
            elif status == "skipped":
                result["skipped"] += 1

        elif current_test is not None and current_test["status"] == "failed":
            if line.startswith(("E ", ">")):
                if current_test["failureMessage"] is None:
                    current_test["failureMessage"] = ""
                current_test["failureMessage"] += line[2:] + "\n"
                current_test["output"].append(line)

        elif "warning" in line.lower() and not line.startswith(("E ", ">")):
            result["warnings"].append(line)

    return result

async def run_pytest(env: Environment) -> Dict[str, Any]:
    result = {
        "framework": TestFramework.PYTEST.value,
        "success": False
    }
    
    try:
        command = "uv pip install pytest pytest-asyncio pytest-mock pytest-cov"
        process = await run_command(command, str(env.work_dir), env.env_vars)
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            result["error"] = f"Failed to install pytest: {stderr.decode() if stderr else ''}"
            return result

        process = await run_command(
            "uv pip freeze",
            str(env.work_dir),
            env.env_vars
        )
        stdout, stderr = await process.communicate()
        logger.debug("Installed packages", extra={"packages": stdout.decode() if stdout else ""})

        process = await run_command(
            "uv run pytest --color=yes -v tests/",
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
            "stdout": output,
            "stderr": errors,
            "results": result
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
