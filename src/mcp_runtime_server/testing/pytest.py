"""Pytest test runner implementation"""
from pathlib import Path
import json
from typing import Any, dict

from mcp_runtime_server.types import Environment
from mcp_runtime_server.sandboxes.sandbox import run_sandboxed_command
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


def build_pytest_command(test_dir: Path) -> str:
    """Build pytest command with proper arguments"""
    return f"python -m pytest -v --json-report-file=- {test_dir}"


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
    
    if process.returncode != 0 and not stdout:
        error = stderr.decode() if stderr else "No error output"
        logger.error({
            "event": "pytest_execution_failed", 
            "error": error,
            "return_code": process.returncode
        })
        raise RuntimeError(f"Failed to execute pytest: {error}")

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        logger.error({
            "event": "pytest_output_invalid",
            "error": str(e),
            "stdout": stdout.decode() if stdout else None,
            "stderr": stderr.decode() if stderr else None
        })
        raise ValueError("Invalid pytest JSON output")
