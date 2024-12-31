"""Test framework utilities."""
import json
import logging
import re
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional

from mcp_runtime_server.commands import run_command
from mcp_runtime_server.types import Environment
from mcp_runtime_server.testing.results import parse_pytest_output

logger = logging.getLogger("mcp_runtime_server.testing.frameworks")

class TestFramework(str, Enum):
    PYTEST = "pytest"

def detect_frameworks(project_dir: str) -> List[TestFramework]:
    """Detect test frameworks in a project directory."""
    path = Path(project_dir)
    frameworks = set()
    
    tests_dir = path / 'tests'
    if tests_dir.exists():
        logger.info(json.dumps({
            "event": "test_directory_found",
            "path": str(tests_dir)
        }))
        conftest_path = tests_dir / 'conftest.py'
        if conftest_path.exists():
            frameworks.add(TestFramework.PYTEST)
            logger.info(json.dumps({
                "event": "pytest_config_found",
                "path": str(conftest_path)
            }))

    logger.info(json.dumps({
        "event": "frameworks_detected",
        "frameworks": [f.value for f in frameworks]
    }))
    return list(frameworks)

async def run_pytest(env: Environment) -> Dict[str, Any]:
    """Run pytest in the environment."""
    result = {
        "framework": TestFramework.PYTEST.value,
        "success": False
    }
    
    try:
        command = "uv pip install pytest pytest-asyncio pytest-mock pytest-cov pytest-json"
        process = await run_command(command, str(env.work_dir), env.env_vars)
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error = stderr.decode() if stderr else ''
            result["error"] = f"Failed to install pytest: {error}"
            logger.error(json.dumps({
                "event": "pytest_install_failed",
                "error": error
            }))
            return result

        logger.info(json.dumps({
            "event": "pytest_starting",
            "working_dir": str(env.work_dir)
        }))
        
        process = await run_command(
            "uv run pytest",
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
        
        logger.info(json.dumps({
            "event": "pytest_complete",
            "total": summary["total"],
            "passed": summary["passed"], 
            "failed": summary["failed"],
            "skipped": summary["skipped"]
        }))
        
    except Exception as e:
        result["error"] = str(e)
        logger.error(json.dumps({
            "event": "pytest_error",
            "error": str(e)
        }))
        
    return result

async def run_framework_tests(framework: TestFramework, env: Environment) -> Dict[str, Any]:
    """Run tests for a specific framework in the environment."""
    logger.info(json.dumps({
        "event": "framework_test_start",
        "framework": framework.value,
        "working_dir": str(env.work_dir)
    }))
    
    if framework == TestFramework.PYTEST:
        result = await run_pytest(env)
        logger.info(json.dumps({
            "event": "framework_test_complete",
            "framework": framework.value,
            "success": result["success"]
        }))
        return result
    else:
        error = f"Unsupported framework: {framework}"
        logger.error(json.dumps({
            "event": "framework_test_error", 
            "error": error
        }))
        raise ValueError(error)