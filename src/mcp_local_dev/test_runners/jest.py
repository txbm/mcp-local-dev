"""Runner implementation for Jest"""

from typing import Dict, Any
import json
from mcp_local_dev.types import Environment, RunnerType, Runtime, CoverageResult
from mcp_local_dev.logging import get_logger
from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command, is_command_available

logger = get_logger(__name__)

def parse_jest_coverage(coverage_map: dict) -> CoverageResult:
    """Parse Jest coverage data into standardized format"""
    files = {}
    total_lines = 0
    total_covered_lines = 0
    total_statements = 0
    total_covered_statements = 0
    total_branches = 0
    total_covered_branches = 0
    total_functions = 0
    total_covered_functions = 0
    
    for file_path, file_coverage in coverage_map.items():
        s = file_coverage.get("s", {})  # Statement map
        b = file_coverage.get("b", {})  # Branch map
        f = file_coverage.get("f", {})  # Function map
        
        # Calculate statement coverage
        covered_statements = sum(1 for hit in s.values() if hit > 0)
        total_statements += len(s)
        total_covered_statements += covered_statements
        
        # Calculate branch coverage
        covered_branches = sum(1 for hits in b.values() if any(h > 0 for h in hits))
        total_branches += len(b)
        total_covered_branches += covered_branches
        
        # Calculate function coverage
        covered_functions = sum(1 for hit in f.values() if hit > 0)
        total_functions += len(f)
        total_covered_functions += covered_functions
        
        # Use statement coverage for line coverage
        total_lines += len(s)
        total_covered_lines += covered_statements
        
        # Calculate file coverage percentage
        if len(s) > 0:
            files[file_path] = (covered_statements / len(s)) * 100
    
    return CoverageResult(
        lines=(total_covered_lines / total_lines * 100) if total_lines > 0 else 0,
        statements=(total_covered_statements / total_statements * 100) if total_statements > 0 else 0,
        branches=(total_covered_branches / total_branches * 100) if total_branches > 0 else 0,
        functions=(total_covered_functions / total_functions * 100) if total_functions > 0 else 0,
        files=files
    )

async def run_jest(env: Environment) -> Dict[str, Any]:
    """Run Jest and parse results"""
    cmd_prefix = "bun" if env.runtime_config.name == Runtime.BUN else "node --experimental-vm-modules"
    # Install coverage dependencies
    await run_sandboxed_command(
        env.sandbox,
        "npm install -D jest-coverage-badges --legacy-peer-deps"
    )
    
    cmd = f"{cmd_prefix} node_modules/jest/bin/jest.js --coverage --json --coverageReporters=json-summary"
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
