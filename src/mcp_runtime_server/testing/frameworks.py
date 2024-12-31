"""Test framework utilities."""
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
        logger.debug("Found tests directory", extra={'data': {'path': str(tests_dir)}})
        conftest_path = tests_dir / 'conftest.py'
        if conftest_path.exists():
            frameworks.add(TestFramework.PYTEST)
            logger.debug("Found pytest config", extra={'data': {'path': str(conftest_path)}})

    logger.debug("Framework detection complete", extra={'data': {'frameworks': [f.value for f in frameworks]}})
    return list(frameworks)

async def run_pytest(env: Environment) -> Dict[str, Any]:
    """Run pytest in the environment."""
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
        logger.debug("Installed packages", extra={
            'data': {'packages': stdout.decode() if stdout else ""}
        })

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
        
        logger.debug("Pytest execution complete", extra={
            'data': {
                'stdout': output,
                'stderr': errors,
                'results': result
            }
        })
        
    except Exception as e:
        result["error"] = str(e)
        logger.error("Pytest execution failed", extra={
            'data': {'error': str(e)}
        })
        
    return result

async def run_framework_tests(framework: TestFramework, env: Environment) -> Dict[str, Any]:
    """Run tests for a specific framework in the environment."""
    logger.debug("Running framework tests", extra={'data': {'framework': framework.value}})
    if framework == TestFramework.PYTEST:
        return await run_pytest(env)
    else:
        raise ValueError(f"Unsupported framework: {framework}")