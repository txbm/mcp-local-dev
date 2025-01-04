"""Test runner utilities."""
import shutil
from typing import Dict, Any, List, Callable, Awaitable

from mcp_runtime_server.types import Environment, TestRunnerType, RunConfig, Runtime
from mcp_runtime_server.logging import get_logger
from mcp_runtime_server.sandboxes.sandbox import run_sandboxed_command

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
        "runner": TestRunnerType.PYTEST.value,
        "success": process.returncode in (0, 1),
        "summary": summary,
        "tests": tests,
        "stdout": stdout_text,
        "stderr": stderr_text
    }

# Test runner registry as a dict of detection and execution functions
TEST_RUNNERS: Dict[TestRunnerType, tuple[Callable[[Environment], bool], Callable[[Environment], Awaitable[Dict[str, Any]]]]] = {
    TestRunnerType.PYTEST: (
        lambda env: env.runtime_config.name == Runtime.PYTHON and shutil.which("pytest") is not None,
        run_pytest
    )
}

def detect_test_runners(env: Environment) -> List[TestRunnerType]:
    """Detect available test runners for the environment"""
    logger.info({"event": "test_runner_detection_start", "project_dir": str(env.sandbox.work_dir)})
    
    for runner_type, (can_run, _) in TEST_RUNNERS.items():
        if can_run(env):
            logger.info({"event": "test_runner_detected", "runner": runner_type.value})
            return [runner_type]  # Return first runner found
            
    logger.info({"event": "no_test_runners_detected"})
    return []

async def run_test_runner(config: RunConfig) -> Dict[str, Any]:
    """Run tests using the specified test runner"""
    logger.info({
        "event": "test_runner_start",
        "runner": config.runner.value,
        "working_dir": str(config.env.sandbox.work_dir)
    })

    runner_funcs = TEST_RUNNERS.get(config.runner)
    if not runner_funcs:
        error = f"Unsupported test runner: {config.runner}"
        logger.error({"event": "test_runner_error", "error": error})
        raise ValueError(error)

    _, run_tests = runner_funcs
    result = await run_tests(config.env)
    
    logger.info({
        "event": "test_runner_complete",
        "runner": config.runner.value,
        "success": result["success"],
        "summary": result.get("summary", {})
    })

    return result
