"""Test result parsing and formatting."""

import json
from typing import Any, Dict

from mcp.types import TextContent
from mcp_runtime_server.types import TestCase
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)

def parse_pytest_json(report: Dict[str, Any]) -> Dict[str, Any]:
    """Transform pytest output into structured results"""
    if not isinstance(report, dict):
        logger.error({"event": "invalid_pytest_report", "error": "Report must be a dictionary"})
        raise ValueError("Invalid pytest report format")
        
    stdout = report.get("stdout", "")
    stderr = report.get("stderr", "")
    returncode = report.get("returncode", -1)

    # Initialize counters
    summary = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0
    }
    tests = []

    # Parse test results from output
    for line in stdout.splitlines():
        if "PASSED" in line or "FAILED" in line or "SKIPPED" in line:
            test_name = line.split("::")[1].split()[0] if "::" in line else line
            status = "passed" if "PASSED" in line else "failed" if "FAILED" in line else "skipped"
            test = {
                "nodeid": test_name,
                "outcome": status,
                "stdout": stdout,
                "duration": 0.0
            }
            tests.append(test)
            summary[status] += 1
            summary["total"] += 1

    result = {
        "success": returncode in (0, 1) and summary["failed"] == 0,
        "summary": summary,
        "tests": tests,
        "stdout": stdout,
        "stderr": stderr
    }

    logger.info(
        {
            "event": "test_summary",
            "data": {
                "total": result["summary"]["total"],
                "passed": result["summary"]["passed"],
                "failed": result["summary"]["failed"],
                "skipped": result["summary"]["skipped"],
            },
        }
    )

    return result

def format_test_results(
    runner: str, results: Dict[str, Any]
) -> list[TextContent]:
    """Convert parsed test results into MCP-compatible format."""
    return [
        TextContent(
            text=json.dumps(
                {"success": True, "runners": [{"runner": runner, **results}]}
            ),
            type="text",
        )
    ]
