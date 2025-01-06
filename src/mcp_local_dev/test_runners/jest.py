"""Runner implementation for Jest"""

from typing import Dict, Any
import json
from mcp_local_dev.types import Environment, RunnerType, Runtime, CoverageResult
from mcp_local_dev.logging import get_logger
from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command, is_command_available

logger = get_logger(__name__)

def parse_jest_coverage(coverage_map: dict) -> CoverageResult:
    """Parse Jest coverage data into standardized format"""
    # Calculate totals across all files
    total_covered = {"lines": 0, "statements": 0, "branches": 0, "functions": 0}
    total_total = {"lines": 0, "statements": 0, "branches": 0, "functions": 0}
    files = {}
    
    for file_path, file_coverage in coverage_map.items():
        # Count covered vs total statements
        covered_statements = sum(1 for hit in file_coverage.get("s", {}).values() if hit > 0)
        total_statements = len(file_coverage.get("s", {}))
        
        # Count covered vs total branches
        branch_hits = file_coverage.get("b", {}).values()
        covered_branches = sum(1 for hits in branch_hits if any(h > 0 for h in hits))
        total_branches = len(branch_hits)
        
        # Count covered vs total functions
        covered_functions = sum(1 for hit in file_coverage.get("f", {}).values() if hit > 0)
        total_functions = len(file_coverage.get("f", {}))
        
        # Lines are derived from statements for Jest
        covered_lines = covered_statements
        total_lines = total_statements
        
        # Update totals
        total_covered["statements"] += covered_statements
        total_total["statements"] += total_statements
        total_covered["branches"] += covered_branches
        total_total["branches"] += total_branches
        total_covered["functions"] += covered_functions
        total_total["functions"] += total_functions
        total_covered["lines"] += covered_lines
        total_total["lines"] += total_lines
        
        # Calculate file coverage percentage
        files[file_path] = (covered_lines / total_lines * 100) if total_lines > 0 else 0
    
    # Calculate final percentages
    return CoverageResult(
        lines=(total_covered["lines"] / total_total["lines"] * 100) if total_total["lines"] > 0 else 0,
        statements=(total_covered["statements"] / total_total["statements"] * 100) if total_total["statements"] > 0 else 0,
        branches=(total_covered["branches"] / total_total["branches"] * 100) if total_total["branches"] > 0 else 0,
        functions=(total_covered["functions"] / total_total["functions"] * 100) if total_total["functions"] > 0 else 0,
        files=files
    )

async def run_jest(env: Environment) -> Dict[str, Any]:
    """Run Jest and parse results"""
    cmd_prefix = "bun" if env.runtime_config.name == Runtime.BUN else "node --experimental-vm-modules"
    cmd = f"{cmd_prefix} node_modules/jest/bin/jest.js --coverage --json"
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

    # Parse coverage data if available
    coverage = None
    if "coverageMap" in result:
        coverage = parse_jest_coverage(result["coverageMap"])

    return {
        "runner": RunnerType.JEST.value,
        "success": result["success"],
        "summary": summary,
        "tests": tests,
        "coverage": coverage,
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
