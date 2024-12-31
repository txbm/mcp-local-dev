"""Test framework utilities."""
import json
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any

from mcp_runtime_server.environments.commands import run_command
from mcp_runtime_server.environments.environment import Environment
from mcp_runtime_server.testing.results import parse_pytest_json
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)

class TestFramework(str, Enum):
    PYTEST = "pytest"

def detect_frameworks(project_dir: str) -> List[TestFramework]:
    """Detect test frameworks in a project directory."""
    path = Path(project_dir)
    frameworks = set()
    
    tests_dir = path / 'tests'
    if tests_dir.exists():
        logger.info({"event": "test_directory_found", "path": str(tests_dir)})
        conftest_path = tests_dir / 'conftest.py'
        if conftest_path.exists():
            frameworks.add(TestFramework.PYTEST)
            logger.info({"event": "pytest_config_found", "path": str(conftest_path)})
    
    return list(frameworks)

async def run_pytest(env: Environment) -> Dict[str, Any]:
    """Run pytest in the environment."""
    result = {"framework": TestFramework.PYTEST.value}
    
    try:
        pytest_path = env.bin_dir / "pytest"
        if not pytest_path.exists():
            pytest_path = env.bin_dir / "pytest.exe"
            
        if not pytest_path.exists():
            raise RuntimeError("pytest not found in environment")
            
        process = await run_command(
            f"{pytest_path} -vv --no-header --json-report --json-report-file=- tests/ 2>/dev/stderr",
            str(env.work_dir),
            env.env_vars
        )
        stdout, stderr = await process.communicate()
        
        try:
            report = json.loads(stderr)
            summary = parse_pytest_json(report)
            result.update(summary)
        except json.JSONDecodeError:
            result.update({
                "success": process.returncode == 0,
                "error": "Failed to parse test output",
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else ""
            })
            
    except Exception as e:
        result.update({
            "success": False,
            "error": str(e)
        })
        
    return result

async def run_framework_tests(framework: TestFramework, env: Environment) -> Dict[str, Any]:
    """Run tests for a specific framework in the environment."""
    logger.info({
        "event": "framework_test_start",
        "framework": framework.value,
        "working_dir": str(env.work_dir)
    })
    
    if framework == TestFramework.PYTEST:
        result = await run_pytest(env)
        logger.info({
            "event": "framework_test_complete",
            "framework": framework.value,
            "success": result["success"]
        })
        return result

    error = f"Unsupported framework: {framework}"
    logger.error({"event": "framework_test_error", "error": error})
    raise ValueError(error)