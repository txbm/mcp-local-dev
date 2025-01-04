"""Pytest test runner implementation"""
from pathlib import Path
import json
from typing import Any, Dict

from mcp_runtime_server.types import Environment
from mcp_runtime_server.sandboxes.sandbox import run_sandboxed_command
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


def build_pytest_command(test_dir: Path) -> str:
    """Build pytest command with proper arguments"""
    # Use --verbose and capture JSON output via --json instead of requiring a plugin
    return (
        f"python -m pytest {test_dir} -v "
        "--capture=no "  # Show test output
        "--tb=short "    # Shorter traceback format
        "-p no:warnings" # Disable warning capture to reduce noise
    )


async def run_pytest_for_directory(env: Environment, test_dir: Path) -> dict[str, Any]:
    """Run pytest for a single test directory"""
    cmd = build_pytest_command(test_dir)
    
    logger.debug({
        "event": "running_pytest",
        "command": cmd,
        "directory": str(test_dir)
    })
    
    process = await run_sandboxed_command(
        env.sandbox,
        cmd,
        env.sandbox.env_vars,
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode not in (0, 1):  # pytest returns 1 for test failures
        error = stderr.decode() if stderr else "No error output"
        logger.error({
            "event": "pytest_execution_failed", 
            "error": error,
            "return_code": process.returncode
        })
        raise RuntimeError(f"Failed to execute pytest: {error}")

    # Parse pytest output into our expected format
    stdout_text = stdout.decode() if stdout else ""
    stderr_text = stderr.decode() if stderr else ""
    
    # Basic parsing of pytest output
    result = {
        "tests": [],
        "summary": {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0
        },
        "stdout": stdout_text,
        "stderr": stderr_text
    }

    # Parse test results from output
    for line in stdout_text.splitlines():
        if "PASSED" in line or "FAILED" in line or "SKIPPED" in line:
            test_name = line.split("::")[1].split()[0] if "::" in line else line
            status = "passed" if "PASSED" in line else "failed" if "FAILED" in line else "skipped"
            result["tests"].append({
                "nodeid": test_name,
                "outcome": status,
                "stdout": stdout_text,
                "duration": 0.0  # We don't parse duration for now
            })
            result["summary"][status] += 1
            result["summary"]["total"] += 1

    return result
