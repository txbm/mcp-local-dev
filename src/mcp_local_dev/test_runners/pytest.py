"""Runner implementation for pytest"""

import json
from typing import Dict, Any
from mcp_local_dev.types import Environment, RunnerType, Runtime, CoverageResult
from mcp_local_dev.logging import get_logger
from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command, is_command_available

logger = get_logger(__name__)

def parse_coverage_data(data: dict) -> CoverageResult:
    """Parse coverage.py JSON output into standardized format"""
    totals = data["totals"]
    files = {
        path: summary["line_rate"] * 100 
        for path, summary in data["files"].items()
    }
    
    return CoverageResult(
        lines=totals["line_rate"] * 100,
        statements=totals["statement_rate"] * 100,
        branches=totals["branch_rate"] * 100,
        functions=totals.get("function_rate", 0.0) * 100,
        files=files
    )


async def run_pytest(env: Environment) -> Dict[str, Any]:
    """Run pytest and parse results"""
    # Install coverage dependencies
    await run_sandboxed_command(
        env.sandbox,
        "uv pip install coverage pytest-cov"
    )

    env_vars = {
        "PYTHONPATH": str(env.sandbox.work_dir),
        "COVERAGE_FILE": str(env.sandbox.tmp_dir / ".coverage"),
        **env.sandbox.env_vars
    }

    cmd = (
        "pytest -v --capture=no --tb=short -p no:warnings "
        "--cov --cov-report=json --cov-branch"
    )
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

    # Parse coverage data if available
    coverage = None
    coverage_json = env.sandbox.tmp_dir / "coverage.json"
    if coverage_json.exists():
        with open(coverage_json) as f:
            coverage = parse_coverage_data(json.load(f))

    return {
        "runner": RunnerType.PYTEST.value,
        "success": returncode == 0,
        "summary": summary,
        "tests": tests,
        "coverage": coverage,
    }


async def check_pytest(env: Environment) -> bool:
    """Check if pytest can run in this environment."""
    return env.runtime_config.name == Runtime.PYTHON and await is_command_available(
        env.sandbox, "pytest"
    )
