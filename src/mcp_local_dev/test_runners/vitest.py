"""Runner implementation for Vitest"""

from typing import Dict, Any
import json
from mcp_local_dev.types import Environment, RunnerType, Runtime, CoverageResult
from mcp_local_dev.logging import get_logger
from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command, is_command_available

logger = get_logger(__name__)

def parse_vitest_coverage(coverage_data: dict) -> CoverageResult:
    """Parse Vitest coverage data into standardized format"""
    # Vitest uses v8 coverage format by default
    totals = coverage_data["totals"]
    files = {
        path: data["lines"]["covered"] / data["lines"]["total"] * 100
        for path, data in coverage_data.items()
        if path != "totals"
    }
    
    return CoverageResult(
        lines=totals["lines"]["covered"] / totals["lines"]["total"] * 100,
        statements=totals["statements"]["covered"] / totals["statements"]["total"] * 100,
        branches=totals["branches"]["covered"] / totals["branches"]["total"] * 100,
        functions=totals["functions"]["covered"] / totals["functions"]["total"] * 100,
        files=files
    )

async def run_vitest(env: Environment) -> Dict[str, Any]:
    """Run Vitest and parse results"""
    cmd_prefix = "bun" if env.runtime_config.name == Runtime.BUN else "node --experimental-vm-modules"
    
    # Install coverage dependency if needed
    await run_sandboxed_command(
        env.sandbox,
        "npm install -D @vitest/coverage-v8 --legacy-peer-deps"
    )
    
    cmd = "vitest run --coverage --reporter json"
    returncode, stdout, stderr = await run_sandboxed_command(env.sandbox, cmd)

    if returncode not in (0, 1):
        return {
            "runner": RunnerType.VITEST.value,
            "success": False,
            "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
            "tests": [],
            "error": "Vitest execution failed",
        }

    stdout_text = stdout.decode() if stdout else "{}"
    result = json.loads(stdout_text)
    
    tests = []
    summary = {
        "total": result["numTotalTests"],
        "passed": result["numPassedTests"],
        "failed": result["numFailedTests"],
        "skipped": result["numPendingTests"],
    }

    for test_file in result["testResults"]:
        for test in test_file["assertionResults"]:
            tests.append({
                "nodeid": test["title"],
                "outcome": test["status"],
            })

    # Parse coverage data if available
    coverage = None
    if "coverage" in result:
        coverage = parse_vitest_coverage(result["coverage"])

    return {
        "runner": RunnerType.VITEST.value,
        "success": result["success"],
        "summary": summary,
        "tests": tests,
        "coverage": coverage,
    }

async def check_vitest(env: Environment) -> bool:
    """Check if Vitest can run in this environment."""
    if env.runtime_config.name not in (Runtime.NODE, Runtime.BUN):
        return False
        
    config_exists = any(
        env.sandbox.work_dir.glob(p)
        for p in ["vitest.config.js", "vitest.config.ts", "vite.config.js"]
    )
    return config_exists and await is_command_available(env.sandbox, "vitest")
