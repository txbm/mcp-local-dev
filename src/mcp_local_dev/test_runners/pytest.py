"""Runner implementation for pytest"""

from typing import Dict, Any
from mcp_local_dev.types import Environment, RunnerType, Runtime
from mcp_local_dev.logging import get_logger
from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command, is_command_available

logger = get_logger(__name__)


async def run_pytest(env: Environment) -> Dict[str, Any]:
    """Run pytest and parse results"""
    env_vars = {"PYTHONPATH": str(env.sandbox.work_dir), **env.sandbox.env_vars}

    cmd = "pytest -v --capture=no --tb=short -p no:warnings"
    returncode, stdout, stderr = await run_sandboxed_command(env.sandbox, cmd, env_vars)

    if returncode not in (0, 1):  # pytest returns 1 for test failures
        logger.error({"event": "pytest_execution_failed", "error": stderr.decode()})
        return {
            "runner": RunnerType.PYTEST.value,
            "success": False,
            "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
            "tests": [],
            "stdout": stdout.decode() if stdout else "",
            "stderr": stderr.decode() if stderr else "",
            "error": "Pytest execution failed",
        }

    stdout_text = stdout.decode() if stdout else ""
    stderr_text = stderr.decode() if stderr else ""

    tests = []
    summary = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}

    for line in stdout_text.splitlines():
        if "::" in line and any(
            status in line for status in ["PASSED", "FAILED", "SKIPPED"]
        ):
            test_name = line.split("::")[1].split()[0]
            status = (
                "passed"
                if "PASSED" in line
                else "failed" if "FAILED" in line else "skipped"
            )
            test = {
                "nodeid": test_name,
                "outcome": status,
                # "stdout": stdout_text,
                # "duration": 0.0,
            }
            tests.append(test)
            summary[status] += 1
            summary["total"] += 1

    return {
        "runner": RunnerType.PYTEST.value,
        "success": returncode == 0,
        "summary": summary,
        "tests": tests,
        # "stdout": stdout_text,
        # "stderr": stderr_text,
    }


async def check_pytest(env: Environment) -> bool:
    """Check if pytest can run in this environment."""
    return env.runtime_config.name == Runtime.PYTHON and await is_command_available(
        env.sandbox, "pytest"
    )
