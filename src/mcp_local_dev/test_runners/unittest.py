"""Runner implementation for unittest"""

from typing import Dict, Any
from mcp_local_dev.types import Environment, RunnerType, Runtime
from mcp_local_dev.logging import get_logger
from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command

logger = get_logger(__name__)

async def run_unittest(env: Environment) -> Dict[str, Any]:
    """Run unittest and parse results"""
    env_vars = {"PYTHONPATH": str(env.sandbox.work_dir), **env.sandbox.env_vars}
    
    cmd = "python -m unittest discover -v"
    returncode, stdout, stderr = await run_sandboxed_command(env.sandbox, cmd, env_vars)

    stdout_text = stdout.decode() if stdout else ""
    
    tests = []
    summary = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}

    for line in stdout_text.splitlines():
        if " ... " in line:
            # Parse test name from format: "test_name (test.module.TestClass.test_name)"
            test_path = line.split(" ... ")[0].strip()
            if "(" in test_path:
                test_name = test_path.split("(")[0]
            else:
                test_name = test_path

            # Parse status
            status = "passed" if "ok" in line.lower() else "failed"
            if "skipped" in line.lower():
                status = "skipped"
            
            test = {
                "nodeid": test_name,
                "outcome": status,
            }
            tests.append(test)
            summary[status] += 1
            summary["total"] += 1

    return {
        "runner": RunnerType.UNITTEST.value,
        "success": returncode == 0,
        "summary": summary,
        "tests": tests,
    }

async def check_unittest(env: Environment) -> bool:
    """Check if unittest can run in this environment."""
    if env.runtime_config.name != Runtime.PYTHON:
        return False
    
    test_files = list(env.sandbox.work_dir.rglob("test_*.py"))
    
    for test_file in test_files:
        with open(test_file, 'r') as f:
            content = f.read()
            if any(pattern in content for pattern in [
                'import unittest',
                'from unittest',
                'unittest.TestCase'
            ]):
                return True
    
    return False
