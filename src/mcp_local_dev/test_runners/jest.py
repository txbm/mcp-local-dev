"""Runner implementation for Jest"""

from typing import Dict, Any
import json
from mcp_local_dev.types import Environment, RunnerType, Runtime
from mcp_local_dev.logging import get_logger
from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command, is_command_available

logger = get_logger(__name__)

async def run_jest(env: Environment) -> Dict[str, Any]:
    """Run Jest and parse results"""
    cmd_prefix = "bun" if env.runtime_config.name == Runtime.BUN else "node --experimental-vm-modules"
    cmd = f"{cmd_prefix} node_modules/jest/bin/jest.js --json"
    returncode, stdout, stderr = await run_sandboxed_command(env.sandbox, cmd)

    if returncode not in (0, 1):
        return {
            "runner": RunnerType.JEST.value,
            "success": False,
            "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
            "tests": [],
            "error": "Jest execution failed",
        }

    result = json.loads(stdout.decode())
    
    tests = []
    summary = {
        "total": result["numTotalTests"],
        "passed": result["numPassedTests"],
        "failed": result["numFailedTests"],
        "skipped": result["numPendingTests"],
    }

    for test_result in result["testResults"]:
        for test in test_result["assertionResults"]:
            tests.append({
                "nodeid": test["title"],
                "outcome": test["status"],
            })

    return {
        "runner": RunnerType.JEST.value,
        "success": result["success"],
        "summary": summary,
        "tests": tests,
    }

async def check_jest(env: Environment) -> bool:
    """Check if Jest can run in this environment."""
    if env.runtime_config.name != Runtime.NODE:
        return False
        
    config_exists = any(
        env.sandbox.work_dir.glob(p) 
        for p in ["jest.config.js", "jest.config.mjs", "jest.config.json"]
    )
    return config_exists and await is_command_available(env.sandbox, "jest")
