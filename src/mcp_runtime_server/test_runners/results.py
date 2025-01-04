"""Test result parsing and formatting."""

import json
from typing import Any, Dict

from mcp.types import TextContent
from mcp_runtime_server.types import TestCase
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)

def parse_pytest_json(report: Dict[str, Any]) -> Dict[str, Any]:
    """Transform pytest output into structured results."""
    if not isinstance(report, dict):
        raise ValueError("Invalid pytest report format")
        
    stdout = report.get("stdout", "")
    stderr = report.get("stderr", "")
    returncode = report.get("returncode", -1)

    summary = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}
    tests = []

    for line in stdout.splitlines():
        if any(status in line for status in ["PASSED", "FAILED", "SKIPPED"]):
            test_name = line.split("::")[1].split()[0] if "::" in line else line
            status = next(s.lower() for s in ["passed", "failed", "skipped"] 
                         if s.upper() in line)
            
            tests.append({
                "nodeid": test_name,
                "outcome": status,
                "stdout": stdout,
                "duration": 0.0
            })
            summary[status] += 1
            summary["total"] += 1

    return {
        "success": returncode in (0, 1) and summary["failed"] == 0,
        "summary": summary,
        "tests": tests,
        "stdout": stdout,
        "stderr": stderr
    }

def format_test_results(runner: str, results: Dict[str, Any]) -> list[TextContent]:
    """Convert test results to MCP format"""
    return [
        TextContent(
            text=json.dumps({
                "success": True,
                "runner": runner,
                "test_cases": results.get("tests", []),
                "summary": results.get("summary", {})
            }),
            type="text"
        )
    ]
