"""Test framework utilities."""
import shutil
from typing import Dict, Any, List, Callable, Awaitable

from mcp_local_dev.types import Environment, TestRunnerType, RunConfig, Runtime
from mcp_local_dev.logging import get_logger
from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command

logger = get_logger(__name__)

async def run_pytest(env: Environment) -> Dict[str, Any]:
    """Run pytest and parse results"""
    cmd = "python -m pytest -v --capture=no --tb=short -p no:warnings"
    process = await run_sandboxed_command(env.sandbox, cmd)
    stdout, stderr = await process.communicate()
    
    stdout_text = stdout.decode() if stdout else ""
    stderr_text = stderr.decode() if stderr else ""
    
    summary = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0
    }
    tests = []

    for line in stdout_text.splitlines():
        if "PASSED" in line or "FAILED" in line or "SKIPPED" in line:
            test_name = line.split("::")[1].split()[0] if "::" in line else line
            status = "passed" if "PASSED" in line else "failed" if "FAILED" in line else "skipped"
            test = {
                "nodeid": test_name,
                "outcome": status,
                "stdout": stdout_text,
                "duration": 0.0
            }
            tests.append(test)
            summary[status] += 1
            summary["total"] += 1

    return {
        "framework": TestRunnerType.PYTEST.value,
        "success": process.returncode in (0, 1),
        "summary": summary,
        "tests": tests,
        "stdout": stdout_text,
        "stderr": stderr_text
    }

# Framework registry as a dict of detection and execution functions
FRAMEWORKS: Dict[TestRunnerType, tuple[Callable[[Environment], bool], Callable[[Environment], Awaitable[Dict[str, Any]]]]] = {
    TestRunnerType.PYTEST: (
        lambda env: env.runtime_config.name == Runtime.PYTHON and shutil.which("pytest") is not None,
        run_pytest
    )
}

def detect_frameworks(env: Environment) -> List[TestRunnerType]:
    """Detect available test frameworks for the environment"""
    logger.info({"event": "framework_detection_start", "project_dir": str(env.sandbox.work_dir)})
    
    for framework_type, (can_run, _) in FRAMEWORKS.items():
        if can_run(env):
            logger.info({"event": "framework_detected", "framework": framework_type.value})
            return [framework_type]  # Return first framework found
            
    logger.info({"event": "no_frameworks_detected"})
    return []

async def run_framework_tests(config: RunConfig) -> Dict[str, Any]:
    """Run tests using the specified framework"""
    logger.info({
        "event": "framework_test_start",
        "framework": config.framework.value,
        "working_dir": str(config.env.sandbox.work_dir)
    })

    framework_funcs = FRAMEWORKS.get(config.framework)
    if not framework_funcs:
        error = f"Unsupported framework: {config.framework}"
        logger.error({"event": "framework_test_error", "error": error})
        raise ValueError(error)

    _, run_tests = framework_funcs
    result = await run_tests(config.env)
    
    logger.info({
        "event": "framework_test_complete",
        "framework": config.framework.value,
        "success": result["success"],
        "summary": result.get("summary", {})
    })

    return result
