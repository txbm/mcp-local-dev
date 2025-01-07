"""Runner implementation for Vitest"""

from typing import Dict, Any
import json
import traceback
from mcp_local_dev.types import Environment, RunnerType, Runtime, CoverageResult
from mcp_local_dev.logging import get_logger
from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command, is_command_available

logger = get_logger(__name__)

def parse_vitest_coverage_text(coverage_text: str) -> CoverageResult:
    """Parse Vitest coverage report text format into standardized format"""
    # Extract values from format like:
    # All files |   93.75 |    93.75 |     100 |   93.75 |
    lines = coverage_text.split('\n')
    summary_line = next(line for line in lines if line.startswith('All files'))
    parts = [p.strip() for p in summary_line.split('|')]
    
    # Get file-specific coverage
    files = {}
    for line in lines:
        if line.startswith(' core.js'):
            parts = [p.strip() for p in line.split('|')]
            files[parts[0].strip()] = float(parts[1])
    
    return CoverageResult(
        lines=float(parts[4]),      # % Lines
        statements=float(parts[1]),  # % Stmts
        branches=float(parts[2]),    # % Branch
        functions=float(parts[3]),   # % Funcs
        files=files
    )

async def run_vitest(env: Environment) -> Dict[str, Any]:
    """Run Vitest and parse results"""
    logger.debug({"event": "starting_vitest_run", "work_dir": str(env.sandbox.work_dir)})
    
    cmd_prefix = "bun" if env.runtime_config.name == Runtime.BUN else "node --experimental-vm-modules"
    
    # Install coverage dependency if needed
    await run_sandboxed_command(
        env.sandbox,
        "npm install -D @vitest/coverage-v8 --legacy-peer-deps"
    )
    
    cmd_prefix = "bunx" if env.runtime_config.name == Runtime.BUN else "npx"
    cmd = f"{cmd_prefix} vitest run --coverage --reporter json"
    logger.debug({"event": "running_vitest_cmd", "cmd": cmd})
    returncode, stdout, stderr = await run_sandboxed_command(env.sandbox, cmd)

    if returncode not in (0, 1):
        logger.error({
            "event": "vitest_execution_failed",
            "returncode": returncode,
            "stdout": stdout.decode() if stdout else None,
            "stderr": stderr.decode() if stderr else None
        })
        return {
            "runner": RunnerType.VITEST.value,
            "success": False,
            "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
            "tests": [],
            "error": "Vitest execution failed",
        }

    try:
        stdout_text = stdout.decode() if stdout else ""
        
        # Split the output into JSON and coverage parts
        json_part, _, coverage_part = stdout_text.partition('\n %')
        
        try:
            result = json.loads(json_part)
            
            if not result:
                logger.warning({"event": "vitest_no_results"})
                return {
                    "runner": RunnerType.VITEST.value,
                    "success": False,
                    "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
                    "tests": [],
                    "error": "No test results returned",
                }

            tests = []
            summary = {
                "total": result.get("numTotalTests", 0),
                "passed": result.get("numPassedTests", 0), 
                "failed": result.get("numFailedTests", 0),
                "skipped": result.get("numPendingTests", 0),
            }

            coverage = None
            if coverage_part:
                try:
                    coverage = parse_vitest_coverage_text(f" %{coverage_part}")
                    logger.debug({"event": "vitest_coverage_parsed", "coverage": coverage})
                except Exception as e:
                    logger.warning({"event": "vitest_coverage_parse_error", "error": str(e)})

            return {
                "runner": RunnerType.VITEST.value,
                "success": result.get("success", False),
                "summary": summary,
                "tests": tests,
                "coverage": coverage,
            }
    except Exception as e:
        logger.error({"event": "vitest_parse_error", "error": str(e), "traceback": traceback.format_exc()})
        return {
            "runner": RunnerType.VITEST.value,
            "success": False,
            "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
            "tests": [],
            "error": f"Failed to parse test results: {str(e)}",
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
